from typing import Dict, List, Any
import re


class ComplianceService:
    """Compliance checking service"""
    
    # Risky keywords
    RISKY_KEYWORDS = {
        "必过": "absolute_promise",
        "包过": "absolute_promise",
        "秒批": "absolute_promise",
        "黑户": "sensitive",
        "无视征信": "sensitive",
        "内部渠道": "sensitive",
        "最低息": "absolute_promise",
        "基本都能做": "overconfident",
        "很容易过": "overconfident",
        "不查征信": "sensitive",
        "灰色": "sensitive",
    }
    
    @staticmethod
    def check_compliance(content: str) -> Dict[str, Any]:
        """Perform compliance check"""
        risk_points = []
        risk_score = 0
        
        # Check for risky keywords
        for keyword, risk_type in ComplianceService.RISKY_KEYWORDS.items():
            if keyword in content:
                risk_points.append({
                    "type": risk_type,
                    "text": keyword,
                    "reason": "Contains risky expression",
                    "suggestion": f"Replace '{keyword}' with neutral expression"
                })
                risk_score += 20
        
        # Check for absolute promises
        absolute_patterns = [
            r"(100%|一定|肯定|绝对|必然).*(通过|批准|获批)",
            r"(没有|不会).*问题",
            r"(保证|承诺).*结果",
        ]
        
        for pattern in absolute_patterns:
            if re.search(pattern, content):
                risk_points.append({
                    "type": "absolute_promise",
                    "text": re.search(pattern, content).group(),
                    "reason": "Contains absolute promise",
                    "suggestion": "Use conditional language instead"
                })
                risk_score += 15
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 100),
            "risk_points": risk_points,
            "suggestions": ComplianceService._generate_suggestions(risk_points),
            "is_compliant": risk_level == "low"
        }
    
    @staticmethod
    def _generate_suggestions(risk_points: List[Dict]) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = set()
        
        for point in risk_points:
            if point["type"] == "absolute_promise":
                suggestions.add(
                    "Use conditional language: 'may', 'could', 'possible' instead of absolute terms"
                )
            elif point["type"] == "sensitive":
                suggestions.add(
                    "Remove sensitive financial terms and use neutral language"
                )
            elif point["type"] == "overconfident":
                suggestions.add(
                    "Reduce confidence level - use phrases like 'worth considering' instead"
                )
        
        suggestions.add("Add disclaimer or risk warning")
        
        return list(suggestions)
    
    @staticmethod
    def suggest_correction(content: str, risk_point: Dict) -> str:
        """Suggest text correction for a risk point"""
        corrections = {
            "必过": "可能通过",
            "包过": "有通过的可能性",
            "秒批": "快速审核",
            "黑户": "征信较弱的用户",
            "无视征信": "对征信要求相对宽松",
            "基本都能做": "大部分情况下可行",
            "很容易过": "有较好的通过概率",
        }
        
        for risky, safe in corrections.items():
            content = content.replace(risky, safe)
        
        return content
