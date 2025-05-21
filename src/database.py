import json
import os
from game_data import Player, Item


def load_player(user_id):
    if not os.path.exists("saves.json"):
        return None

    try:
        with open("saves.json", "r") as f:
            saves = json.load(f)
            if str(user_id) in saves:
                data = saves[str(user_id)]
                player = Player(user_id, data["name"])

                # Восстанавливаем основные атрибуты
                for attr in ["health", "max_health", "attack_power", "defense",
                             "gold", "exp", "exp_to_level", "level"]:
                    setattr(player, attr, data[attr])

                # Восстанавливаем инвентарь
                player.inventory = []
                for item_data in data.get("inventory", []):
                    item = Item(
                        item_data["id"],
                        item_data["name"],
                        item_data["type"],
                        item_data["stat"],
                        item_data["value"],
                        item_data["price"]
                    )
                    player.inventory.append(item)

                return player
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None


def save_player(player):
    data = {
        str(player.user_id): {
            "name": player.name,
            "health": player.health,
            "max_health": player.max_health,
            "attack_power": player.attack_power,
            "defense": player.defense,
            "gold": player.gold,
            "exp": player.exp,
            "exp_to_level": player.exp_to_level,
            "level": player.level,
            "inventory": [
                {
                    "id": item.id,
                    "name": item.name,
                    "type": item.type,
                    "stat": item.stat,
                    "value": item.value,
                    "price": item.price
                }
                for item in player.inventory
            ]
        }
    }

    try:
        existing_data = {}
        if os.path.exists("saves.json"):
            with open("saves.json", "r") as f:
                existing_data = json.load(f)

        existing_data.update(data)

        with open("saves.json", "w") as f:
            json.dump(existing_data, f, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")