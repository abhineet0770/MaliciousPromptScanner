"""
Layer 7: Risk Scoring Module
============================
Aggregates outputs from all detection layers into a final risk score.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _load_yaml_config() -> dict:
    """Load default_config.yaml from the project root."""
    try:
        import yaml
        config_path = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load config YAML: {e}. Using hardcoded defaults.")
        return {}


@dataclass
class RiskThresholds:
    safe_max: int = 9
    suspicious_max: int = 19

    @classmethod
    def from_config(cls) -> 'RiskThresholds':
        cfg = _load_yaml_config()
        t = cfg.get('risk_scoring', {}).get('thresholds', {})
        return cls(
            safe_max=t.get('safe_max', 9),
            suspicious_max=t.get('suspicious_max', 19)
        )

    def classify(self, score: int) -> str:
        if score <= self.safe_max:
            return 'SAFE'
        elif score <= self.suspicious_max:
            return 'SUSPICIOUS'
        else:
            return 'MALICIOUS'


class RiskScorer:
    """Calculates final risk score from all detection layers."""

    DEFAULT_WEIGHTS = {
        'keyword_detection': 40,
        'regex_detection': 20,
        'ngram_detection': 15,
        'semantic_similarity': 25,
        'ml_classifier': 20,
        'rule_engine': 15,
        'llm_classifier': 30   # Layer 8 — high weight since LLM is the most accurate
    }

    DEFAULT_CONFIDENCE_MULTIPLIERS = {'low': 0.6, 'medium': 0.85, 'high': 1.0}

    DEFAULT_ADJUSTMENT_BONUSES = {
        'high_confidence_consensus': 15,
        'critical_regex_pattern': 15,
        'dangerous_category': 20,
        'single_weak_trigger_factor': 0.8
    }

    def __init__(
        self,
        weights: Optional[Dict[str, int]] = None,
        thresholds: Optional[RiskThresholds] = None
    ):
        cfg = _load_yaml_config().get('risk_scoring', {})

        # Weights: config overrides defaults
        config_weights = cfg.get('weights', {})
        self.weights = {**self.DEFAULT_WEIGHTS, **config_weights} if config_weights else (weights or self.DEFAULT_WEIGHTS.copy())

        # Thresholds: load from config
        self.thresholds = thresholds or RiskThresholds.from_config()

        # Confidence multipliers: load from config
        cm = cfg.get('confidence_multipliers', {})
        self.CONFIDENCE_MULTIPLIERS = {
            'low':    cm.get('low',    self.DEFAULT_CONFIDENCE_MULTIPLIERS['low']),
            'medium': cm.get('medium', self.DEFAULT_CONFIDENCE_MULTIPLIERS['medium']),
            'high':   cm.get('high',   self.DEFAULT_CONFIDENCE_MULTIPLIERS['high']),
        }

        # Adjustment bonuses: load from config
        ab = cfg.get('adjustment_bonuses', {})
        self.adjustment_bonuses = {
            'high_confidence_consensus':    ab.get('high_confidence_consensus',    self.DEFAULT_ADJUSTMENT_BONUSES['high_confidence_consensus']),
            'critical_regex_pattern':       ab.get('critical_regex_pattern',       self.DEFAULT_ADJUSTMENT_BONUSES['critical_regex_pattern']),
            'dangerous_category':           ab.get('dangerous_category',           self.DEFAULT_ADJUSTMENT_BONUSES['dangerous_category']),
            'single_weak_trigger_factor':   ab.get('single_weak_trigger_factor',   self.DEFAULT_ADJUSTMENT_BONUSES['single_weak_trigger_factor']),
        }

        self.max_score = sum(self.weights.values())

        # Load external rule thresholds for categories & patterns
        self._rule_data = self._load_rule_thresholds()

        logger.info(f"RiskScorer initialized with max score: {self.max_score} | thresholds: safe<={self.thresholds.safe_max}, suspicious<={self.thresholds.suspicious_max}")

    def _load_rule_thresholds(self) -> dict:
        """Load dangerous categories and critical patterns from data/rule_thresholds.json."""
        auto_path = Path(__file__).parent.parent.parent / "data" / "rule_thresholds.json"
        if auto_path.exists():
            try:
                import json as _json
                with open(auto_path, 'r', encoding='utf-8') as f:
                    return _json.load(f)
            except Exception:
                pass
        return {
            "dangerous_categories": ["hacking", "malware", "illegal", "violence"],
            "critical_regex_patterns": ["reveal_system_prompt", "system_prompt_leak"]
        }

    def _get_confidence_multiplier(self, confidence: float) -> float:
        if confidence < 0.4:
            return self.CONFIDENCE_MULTIPLIERS['low']
        elif confidence < 0.7:
            return self.CONFIDENCE_MULTIPLIERS['medium']
        else:
            return self.CONFIDENCE_MULTIPLIERS['high']

    def calculate_score(self, layer_results: List[Dict]) -> Dict:
        layer_scores = {}
        total_score = 0
        triggered_layers = []

        for result in layer_results:
            layer_name = result.get('layer')

            if layer_name not in self.weights:
                continue

            weight = self.weights[layer_name]

            if result.get('triggered', False):
                confidence = result.get('confidence', 0)
                multiplier = self._get_confidence_multiplier(confidence)

                layer_score = weight * multiplier * confidence
                layer_scores[layer_name] = {
                    'score': round(layer_score, 2),
                    'weight': weight,
                    'confidence': round(confidence, 3),
                    'multiplier': multiplier,
                    'triggered': True
                }

                total_score += layer_score
                triggered_layers.append(layer_name)
            else:
                layer_scores[layer_name] = {
                    'score': 0,
                    'weight': weight,
                    'confidence': 0,
                    'multiplier': 0,
                    'triggered': False
                }

        # Use only the weights of layers present in results (not total max)
        # so that scores aren't diluted by layers that haven't run yet (e.g. LLM)
        present_layers = {r.get('layer') for r in layer_results}
        active_max = sum(w for l, w in self.weights.items() if l in present_layers) or self.max_score
        normalized_score = min(int((total_score / active_max) * 100), 100)
        adjusted_score = self._apply_adjustments(normalized_score, layer_results)
        classification = self.thresholds.classify(adjusted_score)
        overall_confidence = self._calculate_overall_confidence(layer_results)

        return {
            'risk_score': adjusted_score,
            'raw_score': round(total_score, 2),
            'max_possible_score': self.max_score,
            'classification': classification,
            'confidence': overall_confidence,
            'layer_breakdown': layer_scores,
            'triggered_layers': triggered_layers,
            'details': {
                'num_layers_triggered': len(triggered_layers),
                'score_percentage': round((adjusted_score / 100) * 100, 2),
                'thresholds': {
                    'safe_max': self.thresholds.safe_max,
                    'suspicious_max': self.thresholds.suspicious_max
                }
            }
        }

    def _apply_adjustments(self, score: int, layer_results: List[Dict]) -> int:
        adjusted = score
        ab = self.adjustment_bonuses

        # Bonus if multiple high-confidence layers triggered
        high_confidence_count = sum(
            1 for r in layer_results
            if r.get('triggered', False) and r.get('confidence', 0) > 0.8
        )
        if high_confidence_count >= 2:
            adjusted += ab['high_confidence_consensus']

        # Bonus for critical regex patterns
        regex_result = self._get_layer_result(layer_results, 'regex_detection')
        if regex_result:
            matches = regex_result.get('matches', [])
            critical_patterns = self._rule_data.get('critical_regex_patterns', ['reveal_system_prompt', 'system_prompt_leak'])
            if any(m.get('name') in critical_patterns for m in matches):
                adjusted += ab['critical_regex_pattern']

        # Bonus if dangerous category detected
        for result in layer_results:
            categories = result.get('categories', [])
            dangerous = self._rule_data.get('dangerous_categories', ['hacking', 'malware', 'illegal', 'violence'])
            if any(cat in categories for cat in dangerous):
                adjusted += ab['dangerous_category']
                break

        # Reduce score if only one weak layer triggered
        triggered = [r for r in layer_results if r.get('triggered', False)]
        if len(triggered) == 1 and triggered[0].get('confidence', 0) < 0.5:
            adjusted = int(adjusted * ab['single_weak_trigger_factor'])

        return min(adjusted, 100)

    def _calculate_overall_confidence(self, layer_results: List[Dict]) -> float:
        triggered_confidences = [
            r.get('confidence', 0) for r in layer_results if r.get('triggered', False)
        ]

        if triggered_confidences:
            return sum(triggered_confidences) / len(triggered_confidences)

        return 0.0

    def _get_layer_result(self, layers: List[Dict], layer_name: str) -> Optional[Dict]:
        for layer in layers:
            if layer.get('layer') == layer_name:
                return layer
        return None

    def get_classification(self, score: int) -> str:
        return self.thresholds.classify(score)


class DecisionEngine:
    """Makes final decision based on risk score and classification."""

    def __init__(self, risk_scorer: Optional[RiskScorer] = None):
        self.risk_scorer = risk_scorer or RiskScorer()

    def decide(self, layer_results: List[Dict]) -> Dict:
        risk_result = self.risk_scorer.calculate_score(layer_results)

        score = risk_result['risk_score']
        classification = risk_result['classification']

        decision_map = {'SAFE': 'ALLOW', 'SUSPICIOUS': 'WARN', 'MALICIOUS': 'BLOCK'}
        decision = decision_map[classification]

        if decision == 'ALLOW':
            reason = "No malicious indicators detected"
            action = "Proceed with request"
        elif decision == 'WARN':
            reason = "Suspicious patterns detected"
            action = "Log and proceed with caution"
        else:
            reason = "Malicious content detected"
            action = "Block request and log for review"

        return {
            'decision': decision,
            'risk_score': score,
            'classification': classification,
            'confidence': risk_result['confidence'],
            'reason': reason,
            'action': action,
            'layer_results': layer_results,
            'risk_details': risk_result,
            'should_block': decision == 'BLOCK',
            'should_log': decision in ['WARN', 'BLOCK']
        }
