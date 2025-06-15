import math

from ..database.models import BasketballPlayerStat, BasketballTeamStat, BasketballShot
from ..database.models import AtBat, BattingOrder, Bullpen, Pitch


####################################################################
####################################################################

 
class BaseballNormalizer:
    
    _Bulpen = Bullpen
    _BattingOrder = BattingOrder
    _AtBat = AtBat
    _Pitch = Pitch 


####################################################################
####################################################################



class BasketballNormalizer:

    _PlayerShots = BasketballShot
    _PlayerStats = BasketballPlayerStat
    _TeamStats = BasketballTeamStat
    

    def _get_shot_zone(self, shot):
        """
        Convert side, sideline offset (side_pct), and baseline offset (base_pct) into a shot zone.
        Offsets are floats between 0 and 1, mapped to court dimensions.
        
        Args:
            side (str): 'R' or 'L'
            side_pct (float): Horizontal offset (0-1)
            base_pct (float): Vertical offset (0-1)
            
        Returns:
            str: Detailed shot zone
        """
        side = shot["side_of_basket"]
        base_pct = float(shot['baseline_offset_percentage'])
        side_pct = float(shot['sideline_offset_percentage'])
        
        # Validate inputs
        if side not in ['R', 'L'] or not (0 <= side_pct <= 1) or not (0 <= base_pct <= 1):
            return "Invalid input values"
        
        side_str = "Right" if side == 'R' else "Left"
        
        # Adjust base_pct for side (positive for R, negative for L)
        base_pct_adjusted = base_pct * (-1 if side == 'R' else 1)
        
        # Calculate distance (assuming basket at (0,0), half-court width=25, length=47)
        x = side_pct * 94  # Horizontal distance from center (0 to 25 feet)
        y = base_pct_adjusted * 50  # Vertical distance from baseline (0 to 47 feet)
        distance = math.sqrt(x**2 + y**2)
        
        # Determine vertical zone based on distance
        if distance < 4:
            zone = "At the Rim"
        elif 4 <= distance < 12:
            zone = "Paint"
            location = "Center" if side_pct <= 0.3 else "Side"
        elif 12 <= distance < 15:
            zone = "Free Throw"
            location = "Line" if side_pct <= 0.2 else "Extended"
        elif 15 <= distance < 22:
            zone = "Mid-Range"
            location = "Top" if side_pct <= 0.2 else "Elbow" if side_pct <= 0.5 else "Wing"
        else:  # distance >= 22
            zone = "Three-Pointer"
            if distance >= 30:
                location = "Logo"
            elif side_pct <= 0.2:
                location = "Top of the Key"
            elif 0.2 < side_pct <= 0.4 and base_pct < 0.5:
                location = "Corner"
            elif 0.2 < side_pct <= 0.6:
                location = "Wing"
            else:
                location = "Deep"
        
        # Combine zones
        if zone == "At the Rim":
            return f"{zone}"
        elif zone == "Paint":
            return f"{side_str} {location} {zone}"
        elif zone == "Free Throw":
            return f"{side_str} {location} Free Throw"
        elif zone == "Three-Pointer":
            return f"{side_str} {location} Three"
        else:
            return f"{side_str} {location} {zone}"



    def _calculate_clutch(self, shot) -> bool:
        """Determine if the shot is in a clutch situation."""
        try:
            mins, secs = map(int, shot["clock"].split(':'))
        except ValueError:
            mins=0
        
        return mins < 5 and abs(int(shot["home_score"]) - int(shot["away_score"])) <= 5

    