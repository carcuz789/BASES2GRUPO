from pymongo import MongoClient
import pymssql
import datetime

# MongoDB client (local)
mongo_client = MongoClient('mongodb://admin:your_password@localhost:27017/')
mongo_db = mongo_client['nba_db']
mongo_collection = mongo_db['player_profiles']

# SQL Server connection (AWS RDS)
sql_conn = pymssql.connect(
    server='bdnba.cvg2ai2eov0z.us-east-2.rds.amazonaws.com',
    user='admin',
    password='Bases2NBAroot',
    database='BDPrincipalNBA'
)

def migrate_player_data():
    cursor = sql_conn.cursor(as_dict=True)
    # Fetch player and team data
    cursor.execute("""
        SELECT cpi.person_id, cpi.display_first_last, cpi.birthdate, cpi.height, cpi.weight, cpi.position,
               t.id as team_id, t.full_name as team_name, t.abbreviation as team_abbr, t.city as team_city
        FROM common_player_info cpi
        JOIN team t ON cpi.team_id = t.id
    """)
    
    for row in cursor:
        player_doc = {
            "_id": row["person_id"],
            "first_name": row["display_first_last"].split()[0] if row["display_first_last"] else "",
            "last_name": " ".join(row["display_first_last"].split()[1:]) if row["display_first_last"] else "",
            "team": {
                "team_id": row["team_id"],
                "full_name": row["team_name"],
                "abbreviation": row["team_abbr"],
                "city": row["team_city"]
            },
            "birthdate": row["birthdate"] if row["birthdate"] else None,
            "height": row["height"],
            "weight": row["weight"],
            "position": row["position"],
            "games": []
        }
        mongo_collection.update_one({"_id": row["person_id"]}, {"$set": player_doc}, upsert=True)

    # Fetch game data (simplified; assumes player-game mapping exists)
    cursor.execute("""
        SELECT g.game_id, g.game  g.game_date, g.pts_home, g.pts_away, g.team_id_home, g.team_id_away
        FROM game g
    """)
    for row in cursor:
        # Add game data to relevant players (requires player-game stats mapping)
        # Placeholder: Update this based on actual player-game data
        pass

    # Create indexes
    mongo_collection.create_index("_id")
    mongo_collection.create_index("team.team_id")
    mongo_collection.create_index("games.game_id")

if __name__ == "__main__":
    migrate_player_data()
    print("Migration completed.")   