"""
Databricks Optimization Module for Nyaya-Sutra

This module provides:
1. Delta Lake table optimization (Z-ordering, partitioning, compaction)
2. Caching layer for frequent queries
3. Performance monitoring and logging
4. Query optimization helpers
"""

import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, current_timestamp
import hashlib


class DeltaTableOptimizer:
    """Optimizes Delta Lake tables for better performance"""
    
    def __init__(self, spark: SparkSession = None):
        self.spark = spark or SparkSession.getActiveSession()
        if not self.spark:
            raise RuntimeError("No active Spark session")
    
    def optimize_ipc_bns_table(
        self, 
        table_name: str = "workspace.default.ipctobns_csv_delta",
        enable_zorder: bool = True,
        compact_files: bool = True
    ) -> Dict[str, Any]:
        """
        Optimize the IPC-BNS mapping table for faster retrieval.
        
        Optimizations:
        - File compaction to reduce small files
        - Z-ordering on ipc_sections column for faster lookups
        - Vacuum old versions
        - Table statistics
        """
        print(f"Optimizing table: {table_name}")
        results = {}
        
        # 1. Compact small files
        if compact_files:
            print("  • Running OPTIMIZE (file compaction)...")
            start = time.time()
            self.spark.sql(f"OPTIMIZE {table_name}")
            compact_time = time.time() - start
            results["compact_time_sec"] = round(compact_time, 2)
            print(f"    ✓ Completed in {compact_time:.2f}s")
        
        # 2. Z-ordering on frequently queried columns
        if enable_zorder:
            print("  • Running Z-ORDER on ipc_sections...")
            start = time.time()
            self.spark.sql(f"OPTIMIZE {table_name} ZORDER BY (ipc_sections)")
            zorder_time = time.time() - start
            results["zorder_time_sec"] = round(zorder_time, 2)
            print(f"    ✓ Completed in {zorder_time:.2f}s")
        
        # 3. Update table statistics
        print("  • Analyzing table statistics...")
        self.spark.sql(f"ANALYZE TABLE {table_name} COMPUTE STATISTICS")
        results["statistics_updated"] = True
        print("    ✓ Statistics updated")
        
        # 4. Get table metrics
        print("  • Collecting table metrics...")
        table_df = self.spark.table(table_name)
        results["row_count"] = table_df.count()
        results["column_count"] = len(table_df.columns)
        print(f"    ✓ Rows: {results['row_count']:,}, Columns: {results['column_count']}")
        
        results["optimized_at"] = datetime.now().isoformat()
        results["table_name"] = table_name
        
        return results
    
    def create_optimized_indexes(
        self,
        table_name: str = "workspace.default.ipctobns_csv_delta"
    ) -> Dict[str, Any]:
        """
        Create bloom filter indexes for faster lookups.
        Note: Bloom filters in Delta Lake require Databricks Runtime 10.0+
        """
        try:
            print(f"Creating bloom filter index on {table_name}...")
            self.spark.sql(f"""
                CREATE BLOOMFILTER INDEX IF NOT EXISTS
                ON TABLE {table_name}
                FOR COLUMNS(ipc_sections)
            """)
            return {"status": "success", "index_created": True}
        except Exception as e:
            print(f"  ⚠ Bloom filter not supported: {str(e)}")
            return {"status": "skipped", "reason": str(e)}
    
    def vacuum_old_versions(
        self,
        table_name: str = "workspace.default.ipctobns_csv_delta",
        retention_hours: int = 168  # 7 days
    ) -> Dict[str, Any]:
        """Remove old file versions to save storage space"""
        print(f"Vacuuming {table_name} (retention: {retention_hours}h)...")
        
        # Set retention period
        self.spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")
        
        self.spark.sql(f"VACUUM {table_name} RETAIN {retention_hours} HOURS")
        
        return {
            "status": "success",
            "retention_hours": retention_hours,
            "vacuumed_at": datetime.now().isoformat()
        }


class QueryCache:
    """In-memory cache for frequent IPC-BNS lookups"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache = {}
        self._timestamps = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, ipc_section: str) -> str:
        """Generate cache key"""
        return f"ipc_{ipc_section}"
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self._timestamps:
            return True
        age = time.time() - self._timestamps[key]
        return age > self.ttl_seconds
    
    def get(self, ipc_section: str) -> Optional[Dict[str, Any]]:
        """Get cached mapping"""
        key = self._generate_key(ipc_section)
        
        if key in self._cache and not self._is_expired(key):
            self.hits += 1
            return self._cache[key]
        
        self.misses += 1
        return None
    
    def set(self, ipc_section: str, mapping_data: Dict[str, Any]):
        """Cache mapping data"""
        key = self._generate_key(ipc_section)
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._timestamps, key=self._timestamps.get)
            del self._cache[oldest_key]
            del self._timestamps[oldest_key]
        
        self._cache[key] = mapping_data
        self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._cache),
            "max_size": self.max_size
        }


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, spark: SparkSession = None):
        self.spark = spark or SparkSession.getActiveSession()
        self.metrics_log = []
    
    def log_query_performance(
        self,
        query_type: str,
        latency_ms: float,
        cache_hit: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a query performance metric"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
            "metadata": metadata or {}
        }
        self.metrics_log.append(entry)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics_log:
            return {"status": "no_data"}
        
        latencies = [m["latency_ms"] for m in self.metrics_log]
        cache_hits = sum(1 for m in self.metrics_log if m["cache_hit"])
        
        return {
            "total_queries": len(self.metrics_log),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "cache_hit_rate_percent": round(cache_hits / len(self.metrics_log) * 100, 2),
            "period_start": self.metrics_log[0]["timestamp"],
            "period_end": self.metrics_log[-1]["timestamp"]
        }
    
    def save_to_table(self, table_name: str = "workspace.default.nyaya_sutra_metrics"):
        """Save metrics log to Delta table"""
        if not self.metrics_log:
            print("No metrics to save")
            return
        
        df = self.spark.createDataFrame(self.metrics_log)
        df.write.format("delta").mode("append").saveAsTable(table_name)
        print(f"✓ Saved {len(self.metrics_log)} metrics to {table_name}")
        self.metrics_log.clear()


class OptimizedIPCBNSRetriever:
    """Optimized IPC-BNS retrieval with caching"""
    
    def __init__(
        self,
        spark: SparkSession = None,
        cache_enabled: bool = True,
        monitor_enabled: bool = True
    ):
        self.spark = spark or SparkSession.getActiveSession()
        self.cache = QueryCache() if cache_enabled else None
        self.monitor = PerformanceMonitor(spark) if monitor_enabled else None
        self.table_name = "workspace.default.ipctobns_csv_delta"
    
    def get_mapping(self, ipc_section: str) -> Optional[Dict[str, Any]]:
        """Get IPC-BNS mapping with caching"""
        start = time.time()
        cache_hit = False
        
        # Try cache first
        if self.cache:
            cached = self.cache.get(ipc_section)
            if cached:
                cache_hit = True
                result = cached
            else:
                result = self._query_from_table(ipc_section)
                if result:
                    self.cache.set(ipc_section, result)
        else:
            result = self._query_from_table(ipc_section)
        
        latency_ms = (time.time() - start) * 1000
        
        # Log performance
        if self.monitor:
            self.monitor.log_query_performance(
                "ipc_bns_mapping",
                latency_ms,
                cache_hit,
                {"ipc_section": ipc_section}
            )
        
        return result
    
    def _query_from_table(self, ipc_section: str) -> Optional[Dict[str, Any]]:
        """Query mapping from Delta table"""
        result = self.spark.table(self.table_name).filter(
            col("ipc_sections") == ipc_section
        ).select(
            "ipc_sections",
            "bns_sections_subsections",
            "subject",
            "summary_of_comparison"
        ).first()
        
        if result:
            return {
                "IPC_Section": result["ipc_sections"],
                "BNS_Section": result["bns_sections_subsections"],
                "Subject": result["subject"],
                "Summary": result["summary_of_comparison"]
            }
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        if self.cache:
            stats["cache"] = self.cache.stats()
        if self.monitor:
            stats["performance"] = self.monitor.get_summary()
        return stats


def setup_optimized_environment(spark: SparkSession = None) -> Dict[str, Any]:
    """Setup and optimize the Databricks environment"""
    
    print("=" * 70)
    print("DATABRICKS OPTIMIZATION SETUP")
    print("=" * 70)
    
    results = {}
    
    # 1. Optimize Delta Table
    print("\n1. Optimizing IPC-BNS Delta Table...")
    optimizer = DeltaTableOptimizer(spark)
    results["table_optimization"] = optimizer.optimize_ipc_bns_table()
    
    # 2. Enable Photon (if available)
    print("\n2. Checking Photon Acceleration...")
    try:
        spark.conf.set("spark.databricks.photon.enabled", "true")
        results["photon_enabled"] = True
        print("  ✓ Photon acceleration enabled")
    except Exception as e:
        results["photon_enabled"] = False
        print(f"  ⚠ Photon not available: {str(e)}")
    
    # 3. Configure Spark for better performance
    print("\n3. Configuring Spark optimizations...")
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    results["adaptive_query_execution"] = True
    print("  ✓ Adaptive Query Execution enabled")
    
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    
    return results
