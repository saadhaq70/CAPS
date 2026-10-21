"""
Streamlit Dashboard Smoke Test Suite
Verifies:
1. Entry point dashboard/app.py syntax and import delegation.
2. Defense Comparison chart generators:
   - Comparative Bar Chart (Final Accuracy)
   - Line Chart (Accuracy vs. FL Round)
   - Loss Comparison Chart
   - Backdoor Attack Success Rate (ASR) Chart
   - Degradation Comparison Chart
3. Summary Metrics Table schema and contents (Self-Healing YES for ASH-FL, N/A for others).
4. Dynamic multi-defense subset selection.
5. Preservation of original ASH-FL telemetry (G, C, H, P, D signals, DPS radar, health status).
"""

import json
import os
import sys
import unittest
import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from defenses.runner import DefenseResult, ComparisonResult, ExperimentConfig
from dashboard.comparison_visualizations import (
    create_comparison_accuracy_bar,
    create_comparison_accuracy_trajectory,
    create_comparison_loss_trajectory,
    create_comparison_degradation_chart,
    create_comparison_backdoor_asr_chart,
    DEFENSE_COLORS,
)
from dashboard.visualizations import (
    create_accuracy_chart,
    create_loss_chart,
    create_dps_radar,
    create_trust_evolution,
    create_aggregation_heatmap,
)
from dashboard.simulator import DashboardSimulator


class TestDashboardSmoke(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results_dir = os.path.join(REPO_ROOT, "results", "defense_comparison")
        cls.backdoor_json = os.path.join(cls.results_dir, "backdoor.json")
        cls.scaling_json = os.path.join(cls.results_dir, "scaling.json")

        assert os.path.exists(cls.backdoor_json), f"Missing {cls.backdoor_json}"
        with open(cls.backdoor_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.defense_results_all = {
            d_name: DefenseResult(**d_dict)
            for d_name, d_dict in data["defense_results"].items()
        }

    def test_01_app_delegation_entrypoint(self):
        """Verify dashboard/app.py exists and successfully loads unified_dashboard."""
        app_path = os.path.join(REPO_ROOT, "dashboard", "app.py")
        self.assertTrue(os.path.exists(app_path), "dashboard/app.py must exist")
        
        # Test importing dashboard.app
        import dashboard.app as dash_app
        self.assertTrue(hasattr(dash_app, "unified_dashboard"))
        print("  ✓ dashboard/app.py entry point and delegation verified")

    def test_02_accuracy_bar_chart(self):
        """Verify Comparative Bar Chart (Final Accuracy)."""
        fig = create_comparison_accuracy_bar(self.defense_results_all)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)
        bar_trace = fig.data[0]
        self.assertEqual(list(bar_trace.x), ["Multi-Krum", "Trimmed Mean", "FLTrust", "ASH-FL"])
        self.assertEqual(len(bar_trace.y), 4)
        for y_val in bar_trace.y:
            self.assertGreaterEqual(y_val, 0.0)
            self.assertLessEqual(y_val, 100.0)
        print("  ✓ Comparative Bar Chart (Final Accuracy) rendered correctly")

    def test_03_accuracy_trajectory_chart(self):
        """Verify Line Chart (Accuracy vs. FL Round)."""
        fig = create_comparison_accuracy_trajectory(self.defense_results_all)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 4)  # 4 defenses
        names = [trace.name for trace in fig.data]
        self.assertIn("ASH-FL", names)
        self.assertIn("Multi-Krum", names)
        self.assertIn("Trimmed Mean", names)
        self.assertIn("FLTrust", names)
        for trace in fig.data:
            self.assertEqual(len(trace.x), 3)  # 3 rounds
            self.assertEqual(len(trace.y), 3)
        print("  ✓ Line Chart (Accuracy vs. FL Round) rendered correctly")

    def test_04_loss_comparison_chart(self):
        """Verify Loss Comparison Chart."""
        fig = create_comparison_loss_trajectory(self.defense_results_all)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 4)
        for trace in fig.data:
            self.assertEqual(len(trace.x), 3)
            for l_val in trace.y:
                self.assertGreater(l_val, 0.0)
        print("  ✓ Loss Comparison Chart rendered correctly")

    def test_05_backdoor_asr_chart(self):
        """Verify Backdoor Attack Success Rate (ASR) Chart."""
        fig = create_comparison_backdoor_asr_chart(self.defense_results_all)
        self.assertIsNotNone(fig)
        bar_trace = fig.data[0]
        self.assertEqual(list(bar_trace.x), ["Multi-Krum", "Trimmed Mean", "FLTrust", "ASH-FL"])
        asrs = list(bar_trace.y)
        for asr in asrs:
            self.assertGreaterEqual(asr, 0.0)
            self.assertLessEqual(asr, 100.0)
        self.assertAlmostEqual(asrs[0], 13.3, delta=0.5)
        print(f"  ✓ Backdoor ASR Chart verified: {asrs}")

    def test_06_degradation_chart(self):
        """Verify Accuracy Degradation Chart."""
        fig = create_comparison_degradation_chart(self.defense_results_all)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 2)  # Clean Baseline and Under Attack traces
        self.assertEqual(fig.data[0].name, "Clean Baseline")
        self.assertEqual(fig.data[1].name, "Under Attack")
        print("  ✓ Accuracy Degradation Chart rendered correctly")

    def test_07_dynamic_subset_selection(self):
        """Verify UI dynamically handles partial defense selections."""
        subset_names = ["Multi-Krum", "ASH-FL"]
        subset_results = {k: v for k, v in self.defense_results_all.items() if k in subset_names}
        
        fig_bar = create_comparison_accuracy_bar(subset_results)
        self.assertEqual(list(fig_bar.data[0].x), subset_names)
        
        fig_traj = create_comparison_accuracy_trajectory(subset_results)
        self.assertEqual(len(fig_traj.data), 2)
        
        fig_asr = create_comparison_backdoor_asr_chart(subset_results)
        self.assertEqual(list(fig_asr.data[0].x), subset_names)
        print("  ✓ Dynamic subset selection (Multi-Krum + ASH-FL) verified")

    def test_08_summary_metrics_table_schema(self):
        """Verify summary table formatting: Self-Healing YES for ASH-FL, N/A for others."""
        table_rows = []
        for name, res in self.defense_results_all.items():
            row = {
                "Defense": name,
                "Type": res.defense_type.replace("_", " ").title(),
                "Final Accuracy": f"{res.final_accuracy:.1%}",
                "Accuracy Drop": f"{res.accuracy_degradation:+.1%}",
                "Final Loss": f"{res.final_loss:.4f}",
                "Backdoor ASR": f"{res.backdoor_asr:.1%}" if res.backdoor_asr is not None else "N/A",
                "Explicit Detection": "Available" if res.supports_explicit_detection else "N/A (Robust Agg)",
                "Self-Healing": "YES (Autonomous FSM)" if res.supports_self_healing else "N/A",
            }
            if res.supports_self_healing:
                row["Recovery Status"] = (
                    f"Attempts: {res.recovery_metrics.get('recovery_attempts', 0)} | "
                    f"State: {res.recovery_metrics.get('final_fsm_state', 'NORMAL')}"
                )
            else:
                row["Recovery Status"] = "N/A"
            table_rows.append(row)

        ash_row = next(r for r in table_rows if r["Defense"] == "ASH-FL")
        mk_row = next(r for r in table_rows if r["Defense"] == "Multi-Krum")
        tm_row = next(r for r in table_rows if r["Defense"] == "Trimmed Mean")
        flt_row = next(r for r in table_rows if r["Defense"] == "FLTrust")

        self.assertEqual(ash_row["Self-Healing"], "YES (Autonomous FSM)")
        self.assertEqual(ash_row["Explicit Detection"], "Available")
        self.assertEqual(mk_row["Self-Healing"], "N/A")
        self.assertEqual(tm_row["Self-Healing"], "N/A")
        self.assertEqual(flt_row["Self-Healing"], "N/A")
        print("  ✓ Summary Metrics Table schema and values verified")

    def test_09_original_telemetry_preservation(self):
        """
        Verify that original ASH-FL telemetry (G, C, H, P, D signals,
        DPS radar charts, health monitor, and FSM) are completely preserved.
        """
        sim_config = {
            "num_clients": 5,
            "num_rounds": 2,
            "random_seed": 42,
            "enable_attack": True,
            "attack_type": "scaling",
            "num_malicious": 1,
            "scale_factor": 50.0,
            "enable_self_healing": True,
            "dps_threshold": 0.55,
            "recovery_rounds": 2,
        }
        simulator = DashboardSimulator(sim_config)
        res = simulator.run_full_simulation()

        self.assertIn("rounds", res)
        self.assertEqual(len(res["rounds"]), 2)
        r1 = res["rounds"][0]

        # Verify G, C, H, P, D signals in round
        for score_key in ["G_scores", "C_scores", "H_scores", "P_scores", "D_scores"]:
            self.assertIn(score_key, r1, f"Missing {score_key}")
            self.assertEqual(len(r1[score_key]), 5)

        # Verify original visualization functions work without regressions
        fig_radar = create_dps_radar(res, client_id=0)
        self.assertIsNotNone(fig_radar)

        fig_acc = create_accuracy_chart(res)
        self.assertIsNotNone(fig_acc)

        fig_loss = create_loss_chart(res)
        self.assertIsNotNone(fig_loss)

        fig_trust = create_trust_evolution(res)
        self.assertIsNotNone(fig_trust)

        fig_heatmap = create_aggregation_heatmap(res)
        self.assertIsNotNone(fig_heatmap)

        print("  ✓ Original ASH-FL telemetry (G/C/H/P/D radar, trust evolution, heatmap) fully preserved")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING STREAMLIT DASHBOARD SMOKE TEST")
    print("=" * 80)
    unittest.main(verbosity=2)
