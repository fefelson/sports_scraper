from datetime import datetime, timedelta
from sqlalchemy.sql import text
from typing import Any, List, Tuple
import pandas as pd

from ..database.models.database import get_db_session
from ..database.models.analytic_tables import StatMetric, LeagueMetric
from ..utils.logging_manager import get_logger



########################################################################################
########################################################################################



class Analytics:

    def __init__(self, leagueId: str):
        self.leagueId = leagueId
        self.logger = get_logger()


    def truncate_tables(self):
        with get_db_session() as session:
            session.execute(text(f"DELETE FROM game_metrics WHERE league_id = '{self.leagueId}'"))
            session.execute(text(f"DELETE FROM stat_metrics WHERE league_id = '{self.leagueId}'"))




    def store_models(self, all_list_models):
        with get_db_session() as session:
            # Add all list objects at once
            session.add_all(all_list_models)



    def process_quantiles(self, metric: str, dataFrame: pd.DataFrame, isMax: bool=True, ) -> Tuple[float, pd.DataFrame]:
        
        if isMax:
            bestValue = dataFrame[metric].max()
            worstValue = dataFrame[metric].min()
        else:
            bestValue = dataFrame[metric].min()
            worstValue = dataFrame[metric].max()
        # Compute the quantiles
        quantiles = dataFrame[metric].quantile([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])

        return (bestValue, worstValue, quantiles)
    

    def get_valid_group(self, entityId: str, dataFrame: pd.DataFrame) -> pd.DataFrame:
        # Count the number of games per entity
        game_counts = dataFrame.groupby(entityId).size().reset_index(name='game_count')

        # Find the maximum game count
        max_games = game_counts['game_count'].max()

        # Keep only entities that have at least 60% of the max game count
        valid_group = game_counts[game_counts['game_count'] >= 0.6 * max_games]

        # Merge back with the original filtered dataset to only keep valid teams
        return dataFrame[dataFrame[entityId].isin(valid_group[entityId])]
    

    def get_time_frames(self, dataFrame: pd.DataFrame) -> List[Tuple[str, pd.DataFrame]]:

        today = datetime.today()
        timeFrames = [("season", dataFrame)]

        # Convert game_date to datetime
        dataFrame['game_date'] = pd.to_datetime(dataFrame['game_date'])

        for label, gameDate in (("2Weeks", today-timedelta(14)), 
                                ("1Month", today-timedelta(30)),
                                ("2Months", today-timedelta(60))):

            # Filter by date range
            timeFrames.append((label, dataFrame[(dataFrame['game_date'] >= gameDate)]))
        return timeFrames
    

    def set_game_metric(self, timeFrame: str, entityType: str, entityId: str, metricLabel: str, dataFrame: pd.DataFrame) -> List[StatMetric]:
        records = []
        for _, row in dataFrame.iterrows():
            records.append(
                GameMetric(
                    league_id=self.leagueId,
                    entity_type=entityType,  # 'team', 'player'
                    entity_id= row[entityId],  # 'team_id', 'opp_id', 'player_id'
                    timeframe=timeFrame,
                    metric_name= metricLabel, # net_rating, off_eff, def_pts
                    value=row[metricLabel],              
                    reference_date= datetime.now()
                )
            )
        return records
    

    def set_stat_metric(self, timeFrame: str, entityType: str, metricLabel: str, dataFrame: pd.DataFrame, isMax: bool=True) -> StatMetric:
        bestValue, worstValue, quants = self.process_quantiles(metricLabel, dataFrame, isMax=isMax)
        return StatMetric(
                league_id= self.leagueId,
                entity_type= entityType,
                timeframe= timeFrame,
                metric_name= metricLabel,
                best_value= bestValue,
                worst_value=worstValue,
                q1 = quants[0.1],                
                q2 = quants[0.2],                
                q4 = quants[0.4],               
                q6 = quants[0.6],                
                q8 = quants[0.8],                
                q9 = quants[0.9],               
                reference_date = datetime.now()    
            )
    

    def set_win_percentage(self, timeFrame: str, metric: str, metricLabel: str, team: pd.DataFrame) -> List[Any]:
        teamRecords = [] 

        dataFrame = (team.groupby("team_id")
             .apply(lambda x: (x[metric] == 1).sum() * 100 / len(x))
             .reset_index(name=metricLabel))
        [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", "team_id", metricLabel, dataFrame)]
        teamRecords.append(self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame))
        return teamRecords
    

    def set_team_roi(self, timeFrame: str, metric: str, team: pd.DataFrame, opponent: pd.DataFrame, reverse: bool=False):
        teamRecords = []
        teams = {"team":team, "opp": opponent}
        for team_opp in ("team", "opp"):
            isTeam = (team_opp == "team")
            metricLabel = f"{team_opp}_{metric}"
            isMax = isTeam if not reverse else not isTeam
            entityId = "team_id" if isTeam else "opp_id"

            dataFrame = teams[team_opp].groupby(entityId).apply(lambda x: ((x[metric].sum()-(len(x) * 100)) / (len(x) * 100))*100 ).reset_index(name=metricLabel)
            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", entityId, metricLabel, dataFrame)]
            teamRecords.append(self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame, isMax=isMax))
        
        return teamRecords
    

    def set_roi(self, timeFrame: str, metric: str, team: pd.DataFrame, reverse: bool=False):
        teamRecords = []
        metricLabel = f"team_{metric}"

        dataFrame = team.groupby("team_id").apply(lambda x: ((x[metric].sum()-(len(x) * 100)) / (len(x) * 100))*100 ).reset_index(name=metricLabel)        
        [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", "team_id", metricLabel, dataFrame)]
        teamRecords.append(self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame, isMax=not reverse))
        return teamRecords







########################################################################################
########################################################################################



class BasketballAnalytics(Analytics):

    def __init__(self, leagueId: str):
        super().__init__(leagueId)


    def _set_average(self, timeFrame: str, entityType: str, entityId: str, metric: str, validGroup: pd.DataFrame, isMax: bool=True) -> List[Any]:
        records = []
        metricLabel = f"{entityType}_{metric}"
        dataFrame = validGroup.groupby(entityId)[metric].mean().reset_index(name=metricLabel)
        [records.append(x) for x in self.set_game_metric(timeFrame, entityType, entityId, metricLabel, dataFrame)]
        records.append( self.set_stat_metric(timeFrame, entityType, metricLabel, dataFrame, isMax=isMax))

        return records
    

    def _set_team_average(self, timeFrame: str, metric: str, team: pd.DataFrame, opponent: pd.DataFrame, reverse: bool=False) -> List[Any]:
        teamRecords = []
        teams = {"team": team, "opp": opponent}
        for team_opp in ("team", "opp"):
            isTeam = (team_opp == "team")
            isMax = isTeam if not reverse else not isTeam
            entityId = "team_id" if isTeam else "opp_id"
            metricLabel = f"{team_opp}_{metric}"
            dataFrame = teams[team_opp].groupby(entityId)[metric].mean().reset_index(name=metricLabel)
            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", entityId, metricLabel, dataFrame)]
            teamRecords.append( self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame, isMax=isMax))
        
        return teamRecords



    def _set_minute_adjusted(self, entityId: str, metric: str, metricLabel: str, validGroup: pd.DataFrame) -> pd.DataFrame:
        dataFrame = validGroup.groupby(entityId).apply(
                lambda x: (x[metric] * (self._minutesPerGame / x['minutes'])).mean()
            ).reset_index(name=metricLabel) 
        return dataFrame
    

    def _set_team_minute_adjusted(self, timeFrame: str, metric: str, offense: pd.DataFrame, defense: pd.DataFrame, reverse: bool=False) -> List[Any]:
        teamRecords = []
        teams = {"off": offense, "def": defense}
        for off_def in ("off", "def"):
            isOffense = (off_def == "off")
            isMax = isOffense if not reverse else not isOffense
            entityId = "team_id" if isOffense else "opp_id"
            metricLabel = f"{off_def}_{metric}"
            dataFrame = self._set_minute_adjusted(entityId, metric, metricLabel, teams[off_def])
            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", entityId, metricLabel, dataFrame)]
            teamRecords.append( self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame, isMax=isMax))
        
        return teamRecords
    

    def _set_one_per_another(self, entityId: str, one: str, another: str, metricLabel: str, validGroup: pd.DataFrame) -> pd.DataFrame: 
        dataFrame = validGroup.groupby(entityId).apply(
                lambda x: (x[one]/x[another]).mean()
            ).reset_index(name=metricLabel) 
        return dataFrame


    def _set_team_one_per_another(self, timeFrame: str, one: str, another: str, offense: pd.DataFrame, defense: pd.DataFrame, reverse: bool=False) -> List[Any]:
        teamRecords = []
        teams = {"off": offense, "def": defense}
        for off_def in ("off", "def"):
            isOffense = (off_def == "off") 
            isMax = isOffense if not reverse else not isOffense
            entityId = "team_id" if isOffense else "opp_id"
            metricLabel = f"{off_def}_{one}_per_{another}"
            dataFrame = self._set_one_per_another(entityId, one, another, metricLabel, teams[off_def])
            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", entityId, metricLabel, dataFrame)]
            teamRecords.append( self.set_stat_metric(timeFrame, "team", metricLabel, dataFrame, isMax=isMax))
        return teamRecords

              
    def _set_efficiency(self, entityId: str, metricLabel: str, dataFrame: pd.DataFrame) -> pd.DataFrame:
        
        efficency = dataFrame.groupby(entityId).apply(
            lambda x: ((x['pts'] * 100) / x['possessions']).mean()
        ).reset_index(name=metricLabel)
        return efficency


    def _set_net_ratings(self, timeFrame: str, offense: pd.DataFrame, defense: pd.DataFrame) -> List[Any]:
        teamRecords = []
        teams = {"off":offense, "def":defense}
        efficiency = {}
        for off_def in ("off", "def"):
            isOffense = (off_def == "off")
            entityId = "team_id" if isOffense else "opp_id"
            metricLabel = f"{off_def}_eff"
            
            efficiency[off_def] = self._set_efficiency(entityId, metricLabel, teams[off_def])
            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", entityId, metricLabel, efficiency[off_def])]
            teamRecords.append( self.set_stat_metric(timeFrame, "team", metricLabel, efficiency[off_def], isMax=isOffense))
            
        # Merge the two DataFrames on team_id
        netRating = efficiency["off"].merge(efficiency["def"], left_on='team_id', right_on='opp_id')
        # Calculate Net Rating
        netRating['net_rating'] = netRating['off_eff'] - netRating['def_eff']
        [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", "team_id", "net_rating", netRating)]
        teamRecords.append( self.set_stat_metric(timeFrame, "team", "net_rating", netRating))
               
        return teamRecords
    

    def _set_rebounds(self, timeFrame: str, offense: pd.DataFrame, defense: pd.DataFrame) -> List[Any]:
        teamRecords = []
        # Merge the offensive and defensive DataFrames on team_id (offense) and opp_id (defense)
        for reb, opp_reb in (("oreb", "dreb"), ("dreb", "oreb")):
            metricLabel = f"{reb}_pct"
            reb_df = offense.merge(defense, left_on='team_id', right_on='opp_id', suffixes=('_off', '_def'))
            reb_df[metricLabel] = reb_df[f"{reb}_off"] / (reb_df[f"{reb}_off"] + reb_df[f"{opp_reb}_def"])
            
            # Keep only relevant columns
            reb_df = reb_df[['team_id_off', metricLabel]]
            # Group by team_id and take the mean OREB% per team
            reb_summary = reb_df.groupby('team_id_off')[metricLabel].mean().reset_index()

            [teamRecords.append(x) for x in self.set_game_metric(timeFrame, "team", "team_id_off", metricLabel, reb_summary)]
            teamRecords.append( self.set_stat_metric(timeFrame, "team", metricLabel, reb_summary))

        return teamRecords


        

    def fetch_team_stats(self, season: int) -> pd.DataFrame:
         with get_db_session() as session:
             query = f"""
                        SELECT * FROM basketball_team_stats
                            INNER JOIN games ON basketball_team_stats.game_id = games.game_id
                            WHERE games.season = {season} AND games.league_id = '{self.leagueId}'
                    """
             return  pd.read_sql(query, session.bind)   


    def fetch_team_gaming(self, season: int) -> pd.DataFrame:  
        with get_db_session() as session:
            query = f"""
             WITH GameBets AS (
                SELECT 
                    team.game_id,
                    team.team_id,
                    team.opp_id,
                    games.game_date,
                    team.spread,
                    team.result,
                    team.result - team.spread AS ats,
                    team.money_line,
                    team.spread_outcome,
                    team.money_outcome,
                    ou.over_under,
                    ou.total,
                    ou.total - ou.over_under AS att,
                    ou.ou_outcome = 1 AS over_outcome,
                    ou.ou_outcome = -1 AS under_outcome,

                    -- Spread ROI
                    CASE 
                        WHEN team.spread_outcome = 1 AND team.spread_line < 0 THEN (10000/(team.spread_line*-1.0)) + 100
                        WHEN team.spread_outcome = 1 AND team.spread_line > 0 THEN team.spread_line + 100
                        WHEN team.spread_outcome = 0 THEN 100
                        ELSE 0 
                    END AS spread_roi,

                    -- Moneyline ROI
                    CASE 
                        WHEN team.money_outcome = 1 AND team.money_line > 0 THEN 100 + team.money_line
                        WHEN team.money_outcome = 1 AND team.money_line < 0 THEN (10000/(team.money_line*-1.0)) + 100
                        WHEN team.money_outcome = 0 THEN 100
                        ELSE 0
                    END AS money_roi,

                    -- Over ROI
                    CASE 
                        WHEN ou.ou_outcome = 1 AND ou.over_line > 0 THEN 100 + ou.over_line
                        WHEN ou.ou_outcome = 1 AND ou.over_line < 0 THEN (10000/(ou.over_line*-1.0)) + 100
                        WHEN ou.ou_outcome = 0 THEN 100
                        ELSE 0 
                    END over_roi,

                    -- Under ROI
                    CASE 
                        WHEN ou.ou_outcome = -1 AND ou.under_line > 0 THEN 100 + ou.under_line
                        WHEN ou.ou_outcome = -1 AND ou.under_line < 0 THEN (10000/(ou.under_line*-1.0)) + 100
                        WHEN ou.ou_outcome = 0 THEN 100
                        ELSE 0 
                    END under_roi

                FROM game_lines AS team
                INNER JOIN over_unders AS ou ON team.game_id = ou.game_id
                INNER JOIN games ON team.game_id = games.game_id AND (team.team_id = games.home_team_id OR team.team_id = games.away_team_id)
                WHERE games.season = {season} AND games.league_id = '{self.leagueId}'
                )

                SELECT * FROM GameBets;
            """
            return  pd.read_sql(query, session.bind)   


    def team_averages_adjusted(self, teamStats: pd.DataFrame) -> List[Any]:

        tableRecords = []
        for timeFrame, dataFrame in self.get_time_frames(teamStats):

            offense = self.get_valid_group("team_id", dataFrame)
            defense = self.get_valid_group("opp_id", dataFrame)

            [tableRecords.append(x) for x in self._set_net_ratings(timeFrame, offense, defense)]
            [tableRecords.append(x) for x in self._set_team_minute_adjusted(timeFrame, "possessions", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_minute_adjusted(timeFrame, "pts", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_minute_adjusted(timeFrame, "fga", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_minute_adjusted(timeFrame, "fta", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_minute_adjusted(timeFrame, "tpa", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_one_per_another(timeFrame, "fgm", "fga", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_one_per_another(timeFrame, "ftm", "fta", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_one_per_another(timeFrame, "tpm", "tpa", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_one_per_another(timeFrame, "ast", "fgm", offense, defense)]
            [tableRecords.append(x) for x in self._set_team_one_per_another(timeFrame, "turnovers", "possessions", offense, defense, reverse=True)]
            [tableRecords.append(x) for x in self._set_rebounds(timeFrame, offense, defense)]
        return tableRecords


    def team_gaming_averages(self, teamGaming: pd.DataFrame) -> List[Any]:
        tableRecords = []

        for timeFrame, dataFrame in self.get_time_frames(teamGaming):

            
            team = self.get_valid_group("team_id", dataFrame)
            opponent = self.get_valid_group("opp_id", dataFrame)

            [tableRecords.append(x) for x in self.set_win_percentage(timeFrame, "money_outcome", "win_pct", team)]
            [tableRecords.append(x) for x in self.set_win_percentage(timeFrame, "spread_outcome", "cover_pct", team)]
            [tableRecords.append(x) for x in self.set_win_percentage(timeFrame, "over_outcome", "over_pct", team)]
            [tableRecords.append(x) for x in self.set_win_percentage(timeFrame, "under_outcome", "under_pct", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "spread", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "result", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "ats", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "over_under", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "total", team)]
            [tableRecords.append(x) for x in self._set_average(timeFrame, "team", "team_id", "att", team)]
            [tableRecords.append(x) for x in self._set_team_average(timeFrame, "money_line", team, opponent)]
            [tableRecords.append(x) for x in self.set_team_roi(timeFrame, "money_roi", team, opponent)]
            [tableRecords.append(x) for x in self.set_team_roi(timeFrame, "spread_roi", team, opponent)]
            [tableRecords.append(x) for x in self.set_roi(timeFrame, "over_roi", team)]
            [tableRecords.append(x) for x in self.set_roi(timeFrame, "under_roi", team)]
        return tableRecords











########################################################################################
########################################################################################



class NBAAnalytics(BasketballAnalytics):

    _minutesPerGame = 48

    def __init__(self):
        super().__init__("NBA")



########################################################################################
########################################################################################



class NCAABAnalytics(BasketballAnalytics):

    _minutesPerGame = 40

    def __init__(self):
        super().__init__("NCAAB")


########################################################################################
########################################################################################



class MLBAnalytics(Analytics):


    def __init__(self):
        super().__init__("MLB")


    

                
