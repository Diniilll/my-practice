import random


class Player:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        self.level = 1
        self.health = 100
        self.max_health = 100
        self.attack_power = 10
        self.defense = 5
        self.gold = 100
        self.exp = 0
        self.exp_to_level = 100
        self.inventory = []

    def attack(self, enemy):
        damage = max(1, self.attack_power - enemy.defense // 2)
        enemy.health -= damage
        return damage

    def take_damage(self, damage):
        actual_damage = max(1, damage - self.defense // 3)
        self.health -= actual_damage
        return actual_damage

    def heal(self, amount):
        self.health = min(self.health + amount, self.max_health)

    def level_up(self):
        if self.exp >= self.exp_to_level:
            self.level += 1
            self.exp -= self.exp_to_level
            self.exp_to_level = int(self.exp_to_level * 1.5)
            self.max_health += 10
            self.health = self.max_health
            self.attack_power += 1
            self.defense += 1
            return True
        return False


class Enemy:
    def __init__(self, name, level, health, damage, defense, reward, exp_reward):
        self.name = name
        self.level = level
        self.max_health = health
        self.health = health
        self.damage = damage
        self.defense = defense
        self.reward = reward
        self.exp_reward = exp_reward

    def attack(self, player):
        return player.take_damage(self.damage)

    @staticmethod
    def generate_random(player):
        enemy_level = max(1, player.level + random.randint(-1, 2))
        scale_factor = 1 + (enemy_level - 1) * 0.2

        enemies = [
            ("Гоблин", 30, 5, 2, 10, 20),
            ("Скелет", 25, 7, 3, 12, 25),
            ("Орк", 40, 10, 5, 15, 30),
            ("Тролль", 50, 12, 4, 20, 40),
            ("Варг", 35, 8, 3, 18, 35),
            ("Драконид", 60, 15, 7, 25, 50)
        ]

        base_enemy = random.choice(enemies)
        return Enemy(
            name=base_enemy[0],
            level=enemy_level,
            health=int(base_enemy[1] * scale_factor),
            damage=int(base_enemy[2] * scale_factor),
            defense=int(base_enemy[3] * scale_factor),
            reward=int(base_enemy[4] * scale_factor * (1 + player.level * 0.1)),
            exp_reward=int(base_enemy[5] * scale_factor * (1 + player.level * 0.1))
        )


class Item:
    id_counter = 1

    def __init__(self, id, name, type, stat, value, price):
        self.id = id
        self.name = name
        self.type = type
        self.stat = stat
        self.value = value
        self.price = price

    @staticmethod
    def generate_weapons(player_level):
        weapons = [
            (1, "Деревянный меч", "weapon", "атака", 3, 50),
            (2, "Бронзовый меч", "weapon", "атака", 5, 100),
            (3, "Железный меч", "weapon", "атака", 8, 200),
            (4, "Стальной меч", "weapon", "атака", 12, 350),
            (5, "Мифриловый меч", "weapon", "атака", 17, 500),
            (6, "Адский клинок", "weapon", "атака", 23, 700),
            (7, "Меч драконов", "weapon", "атака", 30, 1000)
        ]
        max_weapons = min(3 + player_level // 2, 7)
        return [Item(*weapon) for weapon in weapons[:max_weapons]]

    @staticmethod
    def generate_armor(player_level):
        armors = [
            (101, "Кожаная броня", "armor", "защита", 2, 60),
            (102, "Кольчуга", "armor", "защита", 4, 120),
            (103, "Чешуйчатый доспех", "armor", "защита", 6, 200),
            (104, "Латная броня", "armor", "защита", 9, 300),
            (105, "Мифриловая броня", "armor", "защита", 13, 450),
            (106, "Броня мамонта", "armor", "защита", 18, 650),
            (107, "Драконья броня", "armor", "защита", 25, 900)
        ]
        max_armor = min(3 + player_level // 2, 7)
        return [Item(*armor) for armor in armors[:max_armor]]

    @staticmethod
    def generate_potions():
        return [
            Item(201, "Малое зелье здоровья", "potion", "HP", 30, 25),
            Item(202, "Среднее зелье здоровья", "potion", "HP", 60, 50),
            Item(203, "Большое зелье здоровья", "potion", "HP", 100, 90),
            Item(204, "Эликсир здоровья", "potion", "HP", 200, 180)
        ]