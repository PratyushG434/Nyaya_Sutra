"""
Evaluation Metrics Framework for Nyaya-Sutra Legal AI Platform

This module provides comprehensive evaluation metrics for:
1. IPC-BNS Mapping Accuracy
2. CrPC Filtering Accuracy
3. Agent Routing Accuracy
4. Response Time/Latency
5. LLM Response Quality
"""

import time
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, stddev, min as spark_min, max as spark_max


@dataclass
class MetricResult:
    """Container for metric evaluation results"""
    metric_name: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class EvaluationReport:
    """Comprehensive evaluation report"""
    test_name: str
    metrics: List[MetricResult]
    passed: bool
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "metrics": [m.to_dict() for m in self.metrics],
            "passed": self.passed,
            "errors": self.errors,
            "timestamp": self.timestamp
        }
    
    def summary(self) -> str:
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        lines = [
            "=" * 70,
            f"Evaluation Report: {self.test_name}",
            f"Status: {status}",
            f"Timestamp: {self.timestamp}",
            "=" * 70,
            "\nMetrics:"
        ]
        for metric in self.metrics:
            lines.append(f"  • {metric.metric_name}: {metric.value} {metric.unit}")
        
        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  • {error}")
        
        lines.append("=" * 70)
        return "\n".join(lines)


class IPCBNSMappingEvaluator:
    """Evaluates IPC-BNS mapping accuracy"""
    
    def __init__(self, spark: SparkSession = None):
        self.spark = spark or SparkSession.getActiveSession()
        if not self.spark:
            raise RuntimeError("No active Spark session")
    
    def evaluate_mapping_accuracy(
        self, 
        test_cases: List[Dict[str, Any]]
    ) -> EvaluationReport:
        """
        Evaluate IPC-BNS mapping accuracy against ground truth.
        
        test_cases format:
        [
            {
                "ipc_section": "420",
                "expected_bns": "318(4)",
                "document_text": "Sample legal text with Section 420 IPC..."
            },
            ...
        ]
        """
        metrics = []
        errors = []
        
        correct = 0
        total = len(test_cases)
        
        ipc_table = self.spark.table("workspace.default.ipctobns_csv_delta")
        
        for i, test_case in enumerate(test_cases):
            ipc = test_case["ipc_section"]
            expected_bns = test_case["expected_bns"]
            
            # Query actual mapping
            result = ipc_table.filter(col("ipc_sections") == ipc).select("bns_sections_subsections").first()
            
            if result:
                actual_bns = result["bns_sections_subsections"]
                if actual_bns == expected_bns:
                    correct += 1
                else:
                    errors.append(f"Test {i+1}: IPC {ipc} mapped to {actual_bns}, expected {expected_bns}")
            else:
                errors.append(f"Test {i+1}: IPC {ipc} not found in mapping table")
        
        accuracy = (correct / total * 100) if total > 0 else 0
        
        metrics.append(MetricResult(
            metric_name="Mapping Accuracy",
            value=round(accuracy, 2),
            unit="%",
            metadata={"correct": correct, "total": total}
        ))
        
        return EvaluationReport(
            test_name="IPC-BNS Mapping Accuracy",
            metrics=metrics,
            passed=(accuracy >= 95.0),  # 95% threshold
            errors=errors
        )
    
    def evaluate_crpc_filtering(
        self, 
        test_cases: List[Dict[str, Any]]
    ) -> EvaluationReport:
        """
        Evaluate CrPC filtering accuracy.
        
        test_cases format:
        [
            {
                "document_text": "Section 125 CrPC and Section 420 IPC",
                "expected_ipc": ["420"],
                "expected_filtered": ["125"]  # CrPC sections that should be filtered
            },
            ...
        ]
        """
        import sys
        sys.path.append('/Workspace/Repos/cse240001024@iiti.ac.in/Nyaya_Sutra/src')
        from ipc_bns_agent import filter_crpc_sections
        
        metrics = []
        errors = []
        
        correct_filters = 0
        total = len(test_cases)
        
        for i, test_case in enumerate(test_cases):
            text = test_case["document_text"]
            expected_ipc = set(test_case["expected_ipc"])
            expected_filtered = set(test_case.get("expected_filtered", []))
            
            # Simulate extraction (in real scenario, this comes from LLM)
            all_codes = expected_ipc.union(expected_filtered)
            
            # Apply filter
            filtered_codes = set(filter_crpc_sections(list(all_codes), text))
            
            # Check if filtering is correct
            if filtered_codes == expected_ipc and (all_codes - filtered_codes) == expected_filtered:
                correct_filters += 1
            else:
                errors.append(
                    f"Test {i+1}: Got {filtered_codes}, expected {expected_ipc}. "
                    f"Filtered: {all_codes - filtered_codes}, expected filtered: {expected_filtered}"
                )
        
        accuracy = (correct_filters / total * 100) if total > 0 else 0
        
        metrics.append(MetricResult(
            metric_name="CrPC Filtering Accuracy",
            value=round(accuracy, 2),
            unit="%",
            metadata={"correct": correct_filters, "total": total}
        ))
        
        return EvaluationReport(
            test_name="CrPC Filtering Accuracy",
            metrics=metrics,
            passed=(accuracy >= 95.0),
            errors=errors
        )


class LatencyEvaluator:
    """Evaluates response time and latency"""
    
    @staticmethod
    def measure_function_latency(
        func, 
        *args, 
        iterations: int = 10, 
        **kwargs
    ) -> EvaluationReport:
        """Measure latency of a function over multiple iterations"""
        latencies = []
        errors = []
        
        for i in range(iterations):
            try:
                start = time.time()
                result = func(*args, **kwargs)
                end = time.time()
                latencies.append((end - start) * 1000)  # Convert to ms
            except Exception as e:
                errors.append(f"Iteration {i+1} failed: {str(e)}")
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            metrics = [
                MetricResult("Average Latency", round(avg_latency, 2), "ms"),
                MetricResult("Min Latency", round(min_latency, 2), "ms"),
                MetricResult("Max Latency", round(max_latency, 2), "ms"),
            ]
            
            # P95 latency
            sorted_latencies = sorted(latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else max_latency
            metrics.append(MetricResult("P95 Latency", round(p95_latency, 2), "ms"))
            
            passed = avg_latency < 5000  # 5 second threshold
        else:
            metrics = []
            passed = False
        
        return EvaluationReport(
            test_name=f"Latency Test: {func.__name__}",
            metrics=metrics,
            passed=passed,
            errors=errors
        )


def run_comprehensive_evaluation(spark: SparkSession = None) -> Dict[str, EvaluationReport]:
    """Run all evaluation tests and return comprehensive report"""
    
    print("=" * 70)
    print("NYAYA-SUTRA COMPREHENSIVE EVALUATION")
    print("=" * 70)
    
    results = {}
    
    # 1. IPC-BNS Mapping Accuracy
    print("\n1. Testing IPC-BNS Mapping Accuracy...")
    mapping_eval = IPCBNSMappingEvaluator(spark)
    test_cases_mapping = [
        {"ipc_section": "420", "expected_bns": "318(4)"},
        {"ipc_section": "302", "expected_bns": "103(1)"},
        {"ipc_section": "120B", "expected_bns": "61(2)"},
    ]
    results["mapping_accuracy"] = mapping_eval.evaluate_mapping_accuracy(test_cases_mapping)
    print(results["mapping_accuracy"].summary())
    
    # 2. CrPC Filtering Accuracy
    print("\n2. Testing CrPC Filtering Accuracy...")
    test_cases_crpc = [
        {
            "document_text": "Section 125 CrPC and Section 420 IPC",
            "expected_ipc": ["420"],
            "expected_filtered": ["125"]
        },
        {
            "document_text": "IPC 302 and 498A",
            "expected_ipc": ["302", "498A"],
            "expected_filtered": []
        },
    ]
    results["crpc_filtering"] = mapping_eval.evaluate_crpc_filtering(test_cases_crpc)
    print(results["crpc_filtering"].summary())
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    
    return results
