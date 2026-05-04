import math

class SpatialReasoner:
    """
    Evaluates and scores frontier coordinates based on spatial memory.
    This acts as the 'Brain' between the Map (Memory) and the Explorer (Action).
    """
    def __init__(self):
        # High value targets and their specific search radius
        self.target_rules = {
            "shelf": {"bonus_score": 500.0, "radius_m": 2.0},
            "box": {"bonus_score": 200.0, "radius_m": 3.0}
        }

    def evaluate_frontiers(self, frontiers, known_objects, target_class="shelf"):
        """
        Scores each frontier based on its proximity to high-value target objects.
        """
        if not frontiers:
            return None

        best_frontier = None
        highest_score = -float('inf')

        for fx, fy in frontiers:
            score = 0.0
            
            for obj in known_objects:
                if obj['class'] == target_class:
                    dist_to_obj = math.hypot(obj['x'] - fx, obj['y'] - fy)
                    
                    rule = self.target_rules.get(target_class)
                    if rule and dist_to_obj <= rule["radius_m"]:
                        # Reward frontiers that are close to the target object
                        score += rule["bonus_score"]
            
            if score > highest_score:
                highest_score = score
                best_frontier = (fx, fy)

        return best_frontier