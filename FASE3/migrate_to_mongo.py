import pymongo
from pymongo import MongoClient
import pymssql
import datetime
import logging
from pymongo.errors import PyMongoError
from pymssql import OperationalError, DatabaseError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB client (local)
mongo_client = MongoClient('mongodb://admin:1234@localhost:27017/')
mongo_db = mongo_client['nba_db']
mongo_collection = mongo_db['player_profiles']

# SQL Server connection (AWS RDS)


# SQL Server connection (AWS RDS)
try:
    sql_conn = pymssql.connect(
    server='bdnba.cvg2ai2eov0z.us-east-2.rds.amazonaws.com',
    user='admin',
    password='Bases2NBAroot',
    database='BDPrincipalNBA'
)
    logger.info("Connected to AWS RDS SQL Server")
except (OperationalError, DatabaseError) as e:
    logger.error(f"Failed to connect to RDS: {e}")
    exit(1)

def migrate_player_data():
    try:
        cursor = sql_conn.cursor(as_dict=True)
        
        # Step 1: Migrate player and team data
        logger.info("Migrating player and team data...")
        cursor.execute("""
            SELECT pn.player_id, pn.full_name, cpi.birthdate, cpi.height, cpi.weight, cpi.position,
                   t.id as team_id, t.full_name as team_name, t.abbreviation as team_abbr, t.city as team_city
            FROM player_names pn
            LEFT JOIN common_player_info cpi ON pn.player_id = cpi.person_id
            LEFT JOIN team t ON cpi.team_id = t.id
        """)
        
        player_count = 0
        for row in cursor:
            # Split full_name into first_name and last_name
            name_parts = row["full_name"].split() if row["full_name"] else ["", ""]
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            player_doc = {
                "_id": row["player_id"],
                "first_name": first_name,
                "last_name": last_name,
                "full_name": row["full_name"] if row["full_name"] else "",
                "team": {
                    "team_id": row["team_id"] if row["team_id"] else "",
                    "full_name": row["team_name"] if row["team_name"] else "",
                    "abbreviation": row["team_abbr"] if row["team_abbr"] else "",
                    "city": row["team_city"] if row["team_city"] else ""
                },
                "birthdate": row["birthdate"] if row["birthdate"] else None,
                "height": row["height"] if row["height"] else "",
                "weight": row["weight"] if row["weight"] else "",
                "position": row["position"] if row["position"] else "",
                "games": []
            }
            mongo_collection.update_one(
                {"_id": row["player_id"]},
                {"$set": player_doc},
                upsert=True
            )
            player_count += 1
        logger.info(f"Migrated {player_count} players")

        # Step 2: Migrate game data from play_by_play
        logger.info("Migrating game data...")
        cursor.execute("""
            SELECT pbp.game_id, pbp.player1_id, pbp.eventmsgtype, pbp.eventmsgactiontype,
                   g.game_date, g.pts_home, g.pts_away, g.team_id_home, g.team_id_away
            FROM play_by_play pbp
            JOIN game g ON pbp.game_id = g.game_id
            WHERE pbp.player1_id IS NOT NULL
        """)
        
        game_stats = {}
        for row in cursor:
            player_id = row["player1_id"]
            game_id = row["game_id"]
            key = (player_id, game_id)
            
            if key not in game_stats:
                game_stats[key] = {
                    "game_id": game_id,
                    "game_date": row["game_date"] if row["game_date"] else None,
                    "points": 0,
                    "assists": 0,
                    "rebounds": 0,
                    "team_score": float(row["pts_home"]) if row["team_id_home"] == mongo_collection.find_one({"_id": player_id})["team"]["team_id"] else float(row["pts_away"]),
                    "opponent_score": float(row["pts_away"]) if row["team_id_home"] == mongo_collection.find_one({"_id": player_id})["team"]["team_id"] else float(row["pts_home"])
                }
            
            # Parse eventmsgtype for stats (simplified)
            # eventmsgtype: 1=Field Goal Made, 2=Field Goal Missed, 3=Free Throw, 5=Rebound, 6=Turnover, 7=Assist
            if row["eventmsgtype"] == 1:  # Field Goal Made
                game_stats[key]["points"] += 2  # Adjust for 3-pointers if eventmsgactiontype indicates
                if row["eventmsgactiontype"] in [1, 2, 3]:  # Example 3-point actions
                    game_stats[key]["points"] += 1
            elif row["eventmsgtype"] == 3:  # Free Throw
                game_stats[key]["points"] += 1
            elif row["eventmsgtype"] == 5:  # Rebound
                game_stats[key]["rebounds"] += 1
            elif row["eventmsgtype"] == 7:  # Assist
                game_stats[key]["assists"] += 1

        # Update MongoDB with game stats
        game_count = 0
        for (player_id, game_id), stats in game_stats.items():
            mongo_collection.update_one(
                {"_id": player_id},
                {"$push": {"games": stats}}
            )
            game_count += 1
        logger.info(f"Associated stats for {game_count} player-game combinations")

        # Step 3: Create indexes
        logger.info("Creating MongoDB indexes...")
        mongo_collection.create_index("_id")
        mongo_collection.create_index("team.team_id")
        mongo_collection.create_index("games.game_id")
        logger.info("Indexes created")

    except (OperationalError, DatabaseError) as e:
        logger.error(f"SQL error during migration: {e}")
        raise
    except PyMongoError as e:
        logger.error(f"MongoDB error during migration: {e}")
        raise
    finally:
        sql_conn.close()
        logger.info("SQL connection closed")

if __name__ == "__main__":
    try:
        migrate_player_data()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        exit(1)