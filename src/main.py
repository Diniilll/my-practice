import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from game_data import Player, Enemy, Item
import database
import random

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
player = None
current_enemy = None
battle_in_progress = False


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Исследовать", callback_data="explore")],
        [InlineKeyboardButton("Инвентарь", callback_data="inventory")],
        [InlineKeyboardButton("Магазин", callback_data="shop_menu")],
        [InlineKeyboardButton("Статистика", callback_data="stats")],
        [InlineKeyboardButton("Улучшить характеристики", callback_data="upgrade_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player
    user = update.effective_user
    player = database.load_player(user.id) or Player(user.id, user.first_name)

    await update.message.reply_text(
        f"Привет, {user.first_name}! Ты в мире RPG.\nВыбери действие:",
        reply_markup=main_menu_keyboard()
    )


async def handle_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player, current_enemy, battle_in_progress
    query = update.callback_query
    await query.answer()

    if query.data == "fight":
        if not current_enemy:
            current_enemy = Enemy.generate_random(player)

        # Игрок атакует
        damage_dealt = player.attack(current_enemy)

        if current_enemy.health <= 0:
            # Победа
            player.gold += current_enemy.reward
            player.exp += current_enemy.exp_reward
            level_up_msg = ""
            if player.level_up():
                level_up_msg = "\n⭐ Уровень повышен! Теперь ты {} уровня!".format(player.level)
                # При повышении уровня враги становятся сильнее
                current_enemy = Enemy.generate_random(player)

            database.save_player(player)

            await query.edit_message_text(
                f"Ты победил {current_enemy.name} (Ур. {current_enemy.level})!\n"
                f"Нанесено урона: {damage_dealt}\n"
                f"Награда: +{current_enemy.reward} золота, +{current_enemy.exp_reward} опыта{level_up_msg}\n"
                f"Твои HP: {player.health}/{player.max_health}",
                reply_markup=main_menu_keyboard()
            )
            current_enemy = None
            battle_in_progress = False
        else:
            # Монстр атакует
            damage_taken = current_enemy.attack(player)

            if player.health <= 0:
                # Поражение
                await query.edit_message_text(
                    f"Ты проиграл в бою с {current_enemy.name} (Ур. {current_enemy.level})!\n"
                    f"Получено урона: {damage_taken}",
                )
                current_enemy = None
                battle_in_progress = False
            else:
                # Бой продолжается
                keyboard = [
                    [InlineKeyboardButton(f"Атаковать ({player.attack_power} урона)", callback_data="fight")],
                    [InlineKeyboardButton("Убежать", callback_data="run")]
                ]

                # Добавляем кнопку зелья только если оно есть в инвентаре
                if any(item.type == "potion" for item in player.inventory):
                    keyboard.append([InlineKeyboardButton("Использовать зелье", callback_data="use_potion")])

                await query.edit_message_text(
                    f"⚔️ Бой с {current_enemy.name} (Ур. {current_enemy.level}):\n"
                    f"Ты нанес {damage_dealt} урона\n"
                    f"Монстр атакует и наносит {damage_taken} урона\n\n"
                    f"Состояние:\n"
                    f"{current_enemy.name}: {current_enemy.health}/{current_enemy.max_health} HP\n"
                    f"Твои HP: {player.health}/{player.max_health}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )


async def use_potion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player, current_enemy, battle_in_progress
    query = update.callback_query
    await query.answer()

    # Ищем зелья в инвентаре
    potions = [item for item in player.inventory if item.type == "potion"]

    if not potions:
        await query.answer("У тебя нет зелий лечения!")
        return

    # Используем первое найденное зелье
    potion = potions[0]
    player.heal(potion.value)
    player.inventory.remove(potion)
    database.save_player(player)

    # Обновляем сообщение боя
    keyboard = [
        [InlineKeyboardButton(f"Атаковать ({player.attack_power} урона)", callback_data="fight")],
        [InlineKeyboardButton("Убежать", callback_data="run")]
    ]

    if len(potions) > 1:  # Если есть еще зелья
        keyboard.append([InlineKeyboardButton("Использовать зелье", callback_data="use_potion")])

    await query.edit_message_text(
        f"Ты использовал {potion.name} и восстановил {potion.value} HP!\n\n"
        f"⚔️ Бой с {current_enemy.name} (Ур. {current_enemy.level}):\n"
        f"{current_enemy.name}: {current_enemy.health}/{current_enemy.max_health} HP\n"
        f"Твои HP: {player.health}/{player.max_health}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Оружие", callback_data="shop_weapons")],
        [InlineKeyboardButton("Броня", callback_data="shop_armor")],
        [InlineKeyboardButton("Зелья", callback_data="shop_potions")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]

    await query.edit_message_text(
        "🛒 Магазин - Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_weapons_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    weapons = Item.generate_weapons(player.level)
    keyboard = []

    for weapon in weapons:
        owned = any(item.id == weapon.id for item in player.inventory)
        if owned:
            text = f"✓ {weapon.name} (куплено)"
            callback = "owned_item"
        else:
            text = f"{weapon.name} - {weapon.price}💰 (+{weapon.value} атаки)"
            callback = f"buy_{weapon.id}"

        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="shop_menu")])

    await query.edit_message_text(
        "🛒 Магазин оружия:\nВыберите оружие для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_armor_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    armors = Item.generate_armor(player.level)
    keyboard = []

    for armor in armors:
        owned = any(item.id == armor.id for item in player.inventory)
        if owned:
            text = f"✓ {armor.name} (куплено)"
            callback = "owned_item"
        else:
            text = f"{armor.name} - {armor.price}💰 (+{armor.value} защиты)"
            callback = f"buy_{armor.id}"

        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="shop_menu")])

    await query.edit_message_text(
        "🛒 Магазин брони:\nВыберите броню для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_potions_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    potions = Item.generate_potions()
    keyboard = []

    for potion in potions:
        keyboard.append([InlineKeyboardButton(
            f"{potion.name} - {potion.price}💰 (восстанавливает {potion.value} HP)",
            callback_data=f"buy_{potion.id}"
        )])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="shop_menu")])

    await query.edit_message_text(
        "🛒 Магазин зелий:\nВыберите зелье для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player
    query = update.callback_query
    await query.answer()

    item_id = int(query.data.split("_")[1])

    # Ищем предмет во всех категориях магазина
    shop_items = Item.generate_weapons(player.level) + Item.generate_armor(player.level) + Item.generate_potions()
    item = next((i for i in shop_items if i.id == item_id), None)

    if not item:
        await query.edit_message_text(
            "Предмет не найден!",
            reply_markup=main_menu_keyboard()
        )
        return

    if player.gold >= item.price:
        player.gold -= item.price

        if item.type == "potion":
            # Для зелий просто добавляем в инвентарь
            player.inventory.append(item)
            message = f"Ты купил {item.name}! Теперь его можно использовать из инвентаря."
        else:
            # Для снаряжения сразу применяем бонусы
            if item.type == "weapon":
                player.attack_power += item.value
            elif item.type == "armor":
                player.defense += item.value
            player.inventory.append(item)
            message = f"Ты купил {item.name}! Твой {'атака' if item.type == 'weapon' else 'защита'} увеличилась на {item.value}"

        database.save_player(player)

        # Возвращаемся в соответствующую категорию магазина
        if item.type == "weapon":
            await show_weapons_shop(update, context)
        elif item.type == "armor":
            await show_armor_shop(update, context)
        else:
            await show_potions_shop(update, context)
    else:
        await query.answer("Недостаточно золота!")


async def show_upgrade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    upgrade_cost = player.level * 100
    keyboard = [
        [InlineKeyboardButton(f"Увеличить атаку (+2) - {upgrade_cost}💰", callback_data="upgrade_attack")],
        [InlineKeyboardButton(f"Увеличить защиту (+1) - {upgrade_cost}💰", callback_data="upgrade_defense")],
        [InlineKeyboardButton(f"Увеличить здоровье (+20) - {upgrade_cost}💰", callback_data="upgrade_health")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]

    await query.edit_message_text(
        f"🔧 Улучшение характеристик (Ур. {player.level}):\n"
        f"Текущая атака: {player.attack_power}\n"
        f"Текущая защита: {player.defense}\n"
        f"Текущее здоровье: {player.max_health}\n\n"
        f"У тебя есть: {player.gold}💰",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player
    query = update.callback_query
    await query.answer()

    upgrade_type = query.data.split("_")[1]
    upgrade_cost = player.level * 100

    if player.gold >= upgrade_cost:
        player.gold -= upgrade_cost

        if upgrade_type == "attack":
            player.attack_power += 2
            message = "Атака увеличена на 2!"
        elif upgrade_type == "defense":
            player.defense += 1
            message = "Защита увеличена на 1!"
        elif upgrade_type == "health":
            player.max_health += 20
            player.health += 20
            message = "Максимальное здоровье увеличено на 20!"

        database.save_player(player)
        await show_upgrade_menu(update, context)
        await query.answer(message)
    else:
        await query.answer("Недостаточно золота!")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player, current_enemy, battle_in_progress
    query = update.callback_query
    await query.answer()

    if query.data == "explore":
        current_enemy = Enemy.generate_random(player)
        battle_in_progress = True

        await query.edit_message_text(
            f"Ты встретил {current_enemy.name} (Ур. {current_enemy.level})!\n"
            f"Урон: {current_enemy.damage}\n"
            f"Здоровье: {current_enemy.health}/{current_enemy.max_health}\n"
            f"Защита: {current_enemy.defense}\n\n"
            f"Твоя атака: {player.attack_power} урона",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Атаковать ({player.attack_power} урона)", callback_data="fight")],
                [InlineKeyboardButton("Убежать", callback_data="run")]
            ])
        )

    elif query.data == "fight":
        await handle_battle(update, context)

    elif query.data == "use_potion":
        await use_potion(update, context)

    elif query.data == "run":
        if battle_in_progress:
            await query.edit_message_text(
                f"Ты успешно сбежал от {current_enemy.name}!",
                reply_markup=main_menu_keyboard()
            )
            current_enemy = None
            battle_in_progress = False
        else:
            await query.edit_message_text(
                "Нечего убегать!",
                reply_markup=main_menu_keyboard()
            )

    elif query.data == "stats":
        await query.edit_message_text(
            f"📊 Статистика {player.name} (Ур. {player.level}):\n"
            f"❤️ Здоровье: {player.health}/{player.max_health}\n"
            f"⚔️ Атака: {player.attack_power}\n"
            f"🛡️ Защита: {player.defense}\n"
            f"💰 Золото: {player.gold}\n"
            f"🔮 Опыт: {player.exp}/{player.exp_to_level}\n\n"
            f"Следующий уровень: {player.exp_to_level - player.exp} опыта",
            reply_markup=main_menu_keyboard()
        )

    elif query.data == "inventory":
        weapons = [item for item in player.inventory if item.type == "weapon"]
        armor = [item for item in player.inventory if item.type == "armor"]
        potions = [item for item in player.inventory if item.type == "potion"]

        inventory_text = "🎒 Инвентарь:\n"

        if weapons:
            inventory_text += "\n⚔️ Оружие:\n" + "\n".join(
                f"- {item.name} (+{item.value} атаки)" for item in weapons
            )

        if armor:
            inventory_text += "\n🛡️ Броня:\n" + "\n".join(
                f"- {item.name} (+{item.value} защиты)" for item in armor
            )

        if potions:
            inventory_text += "\n🧪 Зелья:\n" + "\n".join(
                f"- {item.name} (восстанавливает {item.value} HP)" for item in potions
            )

        if not any([weapons, armor, potions]):
            inventory_text += "Пусто"

        keyboard = []
        if potions:
            keyboard.append([InlineKeyboardButton("Использовать зелье", callback_data="use_potion")])
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])

        await query.edit_message_text(
            inventory_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "shop_menu":
        await show_shop_menu(update, context)

    elif query.data == "shop_weapons":
        await show_weapons_shop(update, context)

    elif query.data == "shop_armor":
        await show_armor_shop(update, context)

    elif query.data == "shop_potions":
        await show_potions_shop(update, context)

    elif query.data.startswith("buy_"):
        await handle_purchase(update, context)

    elif query.data == "upgrade_stats":
        await show_upgrade_menu(update, context)

    elif query.data.startswith("upgrade_"):
        await handle_upgrade(update, context)

    elif query.data == "owned_item":
        await query.answer("Ты уже купил этот предмет!")

    elif query.data == "back":
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard()
        )


def main():
    application = ApplicationBuilder().token("7557001874:AAHrhfextSR463P6_fCRbENzGzozO-MT20E").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()


if __name__ == "__main__":
    main()