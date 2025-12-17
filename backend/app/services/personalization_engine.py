"""
Personalization Engine - Deep matching based on user interests and passions
Transforms ScholarStream from generic to highly personalized
"""
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()


class PersonalizationEngine:
    """Advanced personalization using interests, passions, and behavior"""
    
    def __init__(self):
        # Interest-to-keyword mapping for intelligent matching
        self.interest_keywords = {
            'artificial intelligence': ['AI', 'machine learning', 'deep learning', 'neural networks', 'NLP', 'computer vision', 'GPT', 'LLM'],
            'web development': ['web', 'frontend', 'backend', 'fullstack', 'React', 'Node.js', 'JavaScript', 'TypeScript', 'Next.js'],
            'cybersecurity': ['security', 'hacking', 'penetration testing', 'bug bounty', 'CTF', 'cryptography', 'ethical hacking'],
            'data science': ['data', 'analytics', 'statistics', 'visualization', 'pandas', 'numpy', 'data analysis'],
            'mobile development': ['mobile', 'iOS', 'Android', 'React Native', 'Flutter', 'Swift', 'Kotlin', 'app development'],
            'blockchain': ['blockchain', 'cryptocurrency', 'Web3', 'smart contracts', 'Ethereum', 'Solidity', 'DeFi'],
            'game development': ['game', 'Unity', '3D', 'graphics', 'Unreal Engine', 'game design', 'gaming'],
            'robotics': ['robotics', 'automation', 'embedded systems', 'Arduino', 'ROS', 'mechatronics', 'IoT'],
            'healthcare tech': ['healthcare', 'medical', 'biotech', 'health informatics', 'telemedicine', 'healthtech'],
            'fintech': ['finance', 'banking', 'payments', 'trading', 'financial technology', 'fintech'],
            'social impact': ['social good', 'nonprofit', 'education', 'accessibility', 'sustainability', 'impact'],
            'entrepreneurship': ['startup', 'business', 'innovation', 'venture', 'founder', 'entrepreneur'],
            'cloud computing': ['cloud', 'AWS', 'Azure', 'GCP', 'serverless', 'DevOps', 'infrastructure'],
            'ui/ux design': ['design', 'UI', 'UX', 'user experience', 'Figma', 'product design', 'interface'],
        }
    
    def calculate_personalized_score(
        self, 
        opportunity: Dict[str, Any], 
        user_profile: Any
    ) -> float:
        """
        Calculate personalized match score (0-100)
        Considers interests, passions, skills, and demographics
        """
        score = 0.0
        max_score = 100.0
        
        # 1. Interest Match (40 points max) - MOST IMPORTANT
        interest_score = self._score_interests(opportunity, user_profile)
        score += interest_score * 0.4
        
        # 2. Passion Alignment (30 points max)
        passion_score = self._score_passions(opportunity, user_profile)
        score += passion_score * 0.3
        
        # 3. Demographic Match (20 points max)
        demographic_score = self._score_demographics(opportunity, user_profile)
        score += demographic_score * 0.2
        
        # 4. Academic Fit (10 points max)
        academic_score = self._score_academics(opportunity, user_profile)
        score += academic_score * 0.1
        
        logger.debug(
            "Personalization score calculated",
            opportunity=opportunity.get('name'),
            interest_score=interest_score,
            passion_score=passion_score,
            demographic_score=demographic_score,
            academic_score=academic_score,
            final_score=score
        )
        
        # Minimum Floor: Every opportunity gets at least 30 points 
        # to avoid showing "0% Match" for new users with empty profiles.
        return max(min(score, max_score), 30.0)
    
    def _score_interests(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on user interests (0-100)"""
        interests = getattr(profile, 'interests', None) or []
        
        if not interests:
            return 50.0  # Neutral score if no interests
        
        user_interests = [i.lower() for i in interests]
        opp_text = self._get_opportunity_text(opp).lower()
        
        matches = 0
        total_keywords = 0
        
        for interest in user_interests:
            # Get keywords for this interest
            keywords = self.interest_keywords.get(interest, [interest])
            total_keywords += len(keywords)
            
            # Check how many keywords match
            for keyword in keywords:
                if keyword.lower() in opp_text:
                    matches += 1
        
        if total_keywords == 0:
            return 50.0
        
        # Calculate match rate
        match_rate = matches / total_keywords
        
        # Boost score if multiple interests match
        if match_rate > 0.5:
            match_rate = min(match_rate * 1.2, 1.0)
        
        return match_rate * 100
    
    def _score_passions(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on user passions (0-100)"""
        # Passions are stored in profile.background or profile.interests
        background = getattr(profile, 'background', None) or []
        
        if not background:
            return 50.0
        
        opp_text = self._get_opportunity_text(opp).lower()
        
        # Check for passion matches
        passion_matches = 0
        for passion in background:
            if isinstance(passion, str) and passion.lower() in opp_text:
                passion_matches += 1
        
        if len(background) == 0:
            return 50.0
        
        match_rate = passion_matches / len(background)
        return match_rate * 100
    
    def _score_demographics(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on demographic match (0-100)"""
        score = 0.0
        checks = 0
        
        eligibility = opp.get('eligibility') or {}
        
        # GPA check
        gpa_min = eligibility.get('gpa_min')
        user_gpa = getattr(profile, 'gpa', None)
        
        if gpa_min and user_gpa:
            checks += 1
            if user_gpa >= gpa_min:
                score += 100
            elif user_gpa >= (gpa_min - 0.3):
                score += 50
        
        # Major check
        required_majors = eligibility.get('majors')
        user_major = getattr(profile, 'major', None)
        
        if required_majors and user_major:
            checks += 1
            if any(major.lower() in user_major.lower() for major in required_majors):
                score += 100
        elif not required_majors:
            # Open to all majors
            checks += 1
            score += 80
        
        # Background check
        required_backgrounds = eligibility.get('backgrounds', [])
        user_background = getattr(profile, 'background', None) or []
        
        if required_backgrounds and user_background:
            checks += 1
            if any(bg in required_backgrounds for bg in user_background):
                score += 100
        
        return (score / checks) if checks > 0 else 50.0
    
    def _score_academics(self, opp: Dict[str, Any], profile: Any) -> float:
        """Score based on academic fit (0-100)"""
        score = 0.0
        
        # Academic status match
        academic_status = getattr(profile, 'academic_status', None)
        
        if academic_status:
            eligibility = opp.get('eligibility') or {}
            grade_levels = eligibility.get('grade_levels', []) or eligibility.get('grades_eligible', [])
            
            if academic_status in grade_levels:
                score += 100
            elif any(level.lower() in academic_status.lower() for level in grade_levels):
                score += 70
            elif not grade_levels:
                # Open to all academic levels
                score += 60
        
        return score
    
    def _get_opportunity_text(self, opp: Dict[str, Any]) -> str:
        """Get all searchable text from opportunity"""
        parts = [
            opp.get('name', ''),
            opp.get('description', ''),
            opp.get('organization', ''),
            ' '.join(opp.get('tags', [])),
        ]
        
        # Add requirements text
        requirements = opp.get('requirements', {})
        if isinstance(requirements, dict):
            skills = requirements.get('skills_needed', [])
            if skills:
                parts.append(' '.join(skills))
        
        return ' '.join(parts)


# Global instance
personalization_engine = PersonalizationEngine()
