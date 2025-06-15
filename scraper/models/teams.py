from datetime import datetime
from sqlalchemy import select
import pandas as pd

from ..database.models.database import get_db_session
from ..database.models.teams import Team
from ..database.models.basketball.basketball_team_stats import BasketballTeamStat


class TeamModel:
    
    def get_ncaab_team_names():
        with get_db_session() as session:
            teams = session.scalars(select(Team).where(Team.league_id == "NCAAB" and Team.division == "D-I")).all()
            return sorted([team.first_name for team in teams])
        

    def search_ncaab_teams(query):
        with get_db_session() as session:
            teams = session.query(Team).filter(
                Team.league_id == "NCAAB",
                Team.first_name.like(f'{query}%')).all()
            return sorted([team.first_name for team in teams])
        
if __name__ == "__main__":
    from pprint import pprint
    pprint(TeamModel.get_ncaab_team_names())