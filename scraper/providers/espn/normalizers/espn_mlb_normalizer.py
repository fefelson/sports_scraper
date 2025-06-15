import math
import re
from itertools import chain
from typing import Any, Dict, List

from .espn_normalizer import ESPNNormalizer
from ....sports.normalizers import BaseballNormalizer

# for debugging
from pprint import pprint


#############################################################################################
#############################################################################################

#plyTypId


# {'5': Pitch - Ball,
# '57': AB Ended,
# '1': New AB,
# '99': Play Ended,
# '21': Strike - Foul,
# '36': Strike - Looking,
# '37': Strike - Swinging,
# '59': Start of Half Inning,
# '58': End of Half Inning,
# '24': In Play - grounded out,
# '2': In Play - Single,
# '22': In Play - Flied Out,
# '32': In Play - Lined Out,
# '3': In Play - Double, 
# '28': In Play - Home Run,
# '33': In Play - Popped Out,
# '15': In Play - grounded into feilders choice,
# '23': In Play - fouled out,
# '44': Throwing Error,
# '52': Stolen Base,
# '26': In Play - Hit by Pitch,
# '54': Runner Advanced on Wild Pitch,
# '13': Strike - Foul Bunt,
# '10': In Play - Reached on Error,
# '35': In Play - Sac Fly,
# '4': In Play - Triple ,
# '42': Caught Stealing,
# '34': In Play - Sac Bunt,
# '80': Automatic Ball,
# '60': In Play - Ground Rule Double,
# '14': In Play - Fielder's Choice,
# '6': In Play - Bunt Single,
# '81': Intentional Ball,
# '49': Runner Picked Off,
# '48': Runner Advanded on passed ball,
# '46': Runner Advanced on fielder's indifference,
# '17': In Play - Bunt ground out,
# '61': Runner Advanced on balk,
# '77': Picked off and caught stealing,
# '84': Automatic Ball,
# '50': runner out on runner's fielders choice ?,
# '19': In Play - Bunt popped out,
# '79': Automatic Strike,
# '62': Catcher Dropped foul ball - at bat continues,
# '85': 134,
# '55': 108,
# '78': 61,
# '20': 56,
# '18': 38,
# '65': 29,
# '7': 5,
# '72': 4,
# '82': 4,
# '29': 2,
# '83': 1}


token_skip = [
    

]

def find_matching_token(input_string):
    """
    Searches for a token string from a list of tokens within the input string.
    Returns the first matching token string, or None if no match is found.
    """
    for token in atbat_tokens:
        # Use re.search to look for the token as a substring
        # Escape the token to handle any special regex characters
        if re.search(token, input_string):
            return atbat_tokens[token]
    return None



#############################################################################################
#############################################################################################



class ESPNMLBNormalizer(BaseballNormalizer, ESPNNormalizer):
    """Normalizer for ESPN Baseball data (MLB)."""

    def __init__(self, leagueId: str):
        super().__init__("MLB", "sport_baseball")


    def _set_atbats(self, data):

        plays = {p["id"]: p for p in data["box"]["plys"]}
        playList = sorted([key for key in plays])

        atBats = []
        try:
            for half_inning in data["pbp"]["pbp"]:

                for atBat in [atBat for atBat in half_inning.get("plays") if not atBat.get("isInfoPlay", False) and not atBat.get("isPitcherChange", False)]:
                   
                    if atBat.get("pitches"):
                        firstPitch = atBat["pitches"][0]
                        lastPitch = atBat["pitches"][-1]
                        gamePlay = plays[atBat["id"]]
                        
                        firstIndex = playList.index(firstPitch["id"])-1
                        firstPlay = plays[playList[firstIndex]]
                        lastPlay = plays[playList[playList.index(lastPitch["id"])]]

                        while int(firstPlay["plyTypId"]) != 1:
                            firstIndex -= 1
                            firstPlay = plays[playList[firstIndex]]
                    
                        players = re.match("(?P<pitcher>.*) pitches to (?P<batter>.*)", firstPlay["txt"])  
                        

                        try:
                            atBats.append({
                                "batter_id": players["batter"],
                                "pitcher_id": players["pitcher"],
                                "team_id": f"mlb.t.{lastPlay['tm']}",
                                "opp_id": f"mlb.t.{lastPlay['tm']}",
                                "plyTypId": lastPlay["plyTypId"],
                                "hitCoords": lastPitch.get("hitCoords")
                            })
                        except KeyError:
                                pass
                        except TypeError:
                            pprint(firstPlay)
                            raise
        except TypeError:
            pass
        except:
            raise
        return atBats


    def _set_pitches(self, data):
        # pprint(webData)

        gameId = data["box"]["gmStrp"]["gid"]
        plays = {p["id"]: p for p in data["box"]["plys"]}
        playList = sorted([key for key in plays])

        pitches = []
        pitch_count = {}
        try:
            for half_inning in data["pbp"]["pbp"]:
                for atBat in [atBat for atBat in half_inning.get("plays") if not atBat.get("isInfoPlay", False) and not atBat.get("isPitcherChange", False)]:
 
                    if atBat.get("pitches"):
                        firstPitch = atBat["pitches"][0]
                        lastPitch = atBat["pitches"][-1]
                        gamePlay = plays[atBat["id"]]
                        
                        firstIndex = playList.index(firstPitch["id"])-1
                        firstPlay = plays[playList[firstIndex]]
                        lastPlay = plays[playList[playList.index(lastPitch["id"])]]

                        while int(firstPlay["plyTypId"]) != 1:
                            firstIndex -= 1
                            firstPlay = plays[playList[firstIndex]]
                    
                        players = re.match("(?P<pitcher>.*) pitches to (?P<batter>.*)", firstPlay["txt"])    
                        balls = 0
                        strikes = 0
                        for pitch in atBat.get("pitches", []):

                            if pitch.get("hitCoords"):
                                hitX = pitch["hitCoords"]['x']
                                hitY = pitch["hitCoords"]['y']
                            else:
                                hitX = None; hitY = None 

                            abResult = pitch["dsc"].lower()
                            if pitch["rslt"].lower() == "foul":
                                pitch["rslt"] = "foul ball"
                            pitchResult = pitch["dsc"].lower() if pitch["rslt"] == "strike" else pitch['rslt'].lower()
                            
                            if pitch["rslt"].lower() == "ball" and balls == 3:
                                abResult = "walk"
                            elif pitch['rslt'].lower() =="strike" and strikes == 2:
                                abResult = "strike out"
                            elif "Batter Reached On Error" in pitch["dsc"]:
                                abResult = "reached on error"

                            
                            
                            pc = pitch_count.get(players["pitcher"], 0)+1
                            pitch_count[players["pitcher"]] = pc                   
                                

                            try:
                                bin_strike = lambda x: (
                                min(max(int((int(x["ptchCoords"]['x']) - 18.4) / 9.64), 0), 19) +
                                min(max(int((int(x["ptchCoords"]['y']) - 97.7) / 7.90), 0), 19) *20
                                )
                                bin = bin_strike(pitch)
                                pitches.append({
                                    "game_id": "FILL IN",
                                    "batter_id": players["batter"],
                                    "pitcher_id": players["pitcher"],
                                    "team_id": f"mlb.t.{firstPlay['tm']}",
                                    "opp_id": f"mlb.t.{lastPlay['tm']}",
                                    "play_num": str(int((round(int(re.sub(gameId, "", pitch["id"])), -2)/10000)-1)),
                                    "pitch_count": pc,
                                    "sequence": pitch.get("count"),
                                    "balls": balls,
                                    "strikes": strikes,
                                    "velocity": pitch["vlcty"],
                                    "pitch_x": pitch["ptchCoords"]['x'],
                                    "pitch_y": pitch["ptchCoords"]['y'],
                                    "pitch_location": bin,
                                    "hit_x": hitX,
                                    "hit_y": hitY,
                                    "pitch_type_name": pitch["ptchDsc"].lower(),
                                    "ab_result_name": abResult if pitchResult != abResult else None,
                                    "pitch_result_name": pitchResult
                                })

                                if pitch['rslt'] == "ball" and balls < 3:
                                    balls+= 1
                                elif strikes <2:
                                    strikes +=1
                            except KeyError:
                                pass
                            except TypeError:
                                print(pitch)
                                raise
                    
        except TypeError:
            pass 
        except:
            raise
        return pitches



    def _set_mlb_player_stats(self, data, *, b_p):
        # pprint(data)
        batter_list = [ath["athlt"] for team in data for ath in team["stats"][0]['athlts'] if ath["athlt"].get("id")]
        pitcher_list = [ath["athlt"] for team in data for ath in team["stats"][1]['athlts'] if ath["athlt"].get("id")]
        athletes = {}
        for player in chain(batter_list, pitcher_list):
            athletes[player["id"]] = player["dspNm"]
        

        playerStats=[]
        try:
            for i in range(2):
                statData = data[i]["stats"][ 0 if b_p == "B" else 1]
                labels = [x.lower() for x in statData["lbls"]]

                for player in statData["athlts"]:
                    try:
                        playerStats.append({
                            "player_id": athletes[player['athlt']['id']],
                            "pos": player['pos'],
                            "stats": dict(zip(labels, player['stats']))
                        })
                    except KeyError:
                        pass
        except:
            raise
        return playerStats



    def _set_player_stats(self, webData):
        # pprint(webData)

        playerStats = {
            "batting": self._set_mlb_player_stats(webData, b_p="B"),
            "pitching": self._set_mlb_player_stats(webData, b_p="P")
        }
        return playerStats


    def _set_misc(self, webData):
        # pprint(webData)
        
        misc = {
            "plays": webData["box"]["plys"],
            "at_bats": self._set_atbats(webData),
            "pitches": self._set_pitches(webData)
        }
        return misc


    def _set_team_stats(self, data: Dict[str, Any]) -> List[Dict]:
        # pprint(data)

        teamStats = []
        try:
            for i in range(2):
                tmData = data["bxscr"][i]["tm"]
                batData = data["bxscr"][i]["stats"][0]
                pitchData = data["bxscr"][i]["stats"][1]  
                a_h = "away" if tmData["id"] == data["shtChrt"]["tms"]["away"]["id"] else "home"

                teamStats.append({
                    "team_id": f"mlb.t.{tmData['id']}",
                    "errors":  data["shtChrt"]["tms"][a_h]["errors"],
                    "batting": dict(zip([x.lower() for x in batData["lbls"]],[x.lower() for x in batData["ttls"]])),
                    "pitching": dict(zip([x.lower() for x in pitchData["lbls"]],[x.lower() for x in pitchData["ttls"]]))
                })
        except:
            raise
        return teamStats  

