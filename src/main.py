#!/usr/bin/env python

import logging
from errno import *
from telegram.error import TelegramError

import re
import random
import requests
import toml
from toml import TomlDecodeError
from enum import Enum, auto, unique
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# <editor-fold desc="[Constants]">
# Consts para keys de dicts
CONTADOR = 'contador'
CONTADOR_MSG = 'contador_msg'
WEATHER_API_KEY = 'WEATHER_API_KEY'


@unique
class Estado(Enum):
    MAIN_MENU = auto()
    CHOOSING_CITY = auto()
    END = ConversationHandler.END


# </editor-fold>


# <editor-fold desc="[Main Menu]">
main_menu_keyboard = ReplyKeyboardMarkup([
    ["¡Quiero saber el clima! ☀️"],
    ["¡Quiero contar! 🔢"],
])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Estado:
    """Empezar conversacion, mostrar menu principal."""
    await update.message.reply_text(
        text="¡Hola! ¿Qué necesitas? 😊\n(Tip: Cancela cualquier comando con /no)",
        reply_markup=main_menu_keyboard,
    )

    if CONTADOR not in context.user_data.keys():
        context.user_data[CONTADOR] = 0

    return Estado.MAIN_MENU


# </editor-fold>


# <editor-fold desc="[Contador]">
contador_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="Reset", callback_data='C0'),
            InlineKeyboardButton(text="Contar", callback_data='C1'),
        ],
    ],
)


async def limpiar_contadores(_, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Eliminar contadores existentes, ya que seran invalidos"""
    # Posiblemente sea mejor eliminar el mensaje, pero hay un limite de 48h para ello
    # Siempre se puede editar, por eso he elegido esto
    if CONTADOR_MSG in context.user_data.keys():
        msg = context.user_data[CONTADOR_MSG]
        await msg.edit_text(
            text=msg.text
        )


async def nuevo_contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Crear un nuevo contador."""
    veces_contadas = f"Veces contadas: {context.user_data.get(CONTADOR)}"

    # Si existe otro mensaje con un contador, eliminarle los botones
    await limpiar_contadores(update, context)

    context.user_data[CONTADOR_MSG] = (
        await update.message.reply_text(
            text=veces_contadas,
            reply_markup=contador_keyboard,
        )
    )


async def actualizar_contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actualizar un contador existente."""
    await update.callback_query.answer()

    if int(update.callback_query.data[1]):
        context.user_data[CONTADOR] += 1
    else:
        context.user_data[CONTADOR] = 0

    try:
        await update.callback_query.edit_message_text(
            text=f"Veces contadas: {context.user_data.get(CONTADOR)}",
            reply_markup=contador_keyboard,
        )
    except TelegramError as e:
        # Si el usuario presiona Reset dos veces, el mensaje no cambiara, lo cual causa una exception
        # No es necesario manejar eso, pero si otras exceptions
        if int(update.callback_query.data[1]):
            raise e


# </editor-fold>


# <editor-fold desc="[Clima]">
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"


# WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/forecast/daily"


async def nuevo_clima(update: Update, _) -> Estado:
    """Iniciar proceso de obtencion del clima"""
    await update.message.reply_text(
        "Ingresa la ciudad de la que quieras ver el clima:",
        reply_markup=None
    )
    return Estado.CHOOSING_CITY


async def obtener_clima(update: Update, _) -> Estado:
    """Obtener clima dada la ciudad proporcionada"""
    ciudad = update.message.text

    # Mensaje de carga
    msg = await update.message.reply_text(
        text=random.choice([
            "Recompilando informacion...",
            "Mirando al cielo...",
            "Testeando aguas...",
            f"Viajando a {ciudad}...",
            "No es mi culpa que los del clima sean tan lentos...",
        ])
    )
    res = requests.get(
        WEATHER_API_URL,
        params={
            'q': ciudad,
            'appid': config[WEATHER_API_KEY],
            'units': 'metric',
            'lang': 'es',
        }
    )

    if not res.ok:
        await msg.edit_text(
            "No pude encontrar esa ciudad.\nIntente con una diferente.\n(/no para cancelar)"
            if res.status_code == 404 else
            "Algo malo ha pasado, intentelo nuevamente.\n(/no para rendirse)"
        )
        return Estado.CHOOSING_CITY

    data = dict(res.json())
    w_main = data['main']
    weather = data['weather']
    min_max_temp = \
        f"\n| ({w_main['temp_min']}°C min | {w_main['temp_max']}°C max)"\
        if 'temp_min' in w_main.keys() \
        else ""
    restext = f"""
    [ {data['name']} ]
{'~' * (len(data['name']) + 4)}
| Temperatura: {w_main['temp']}°C {min_max_temp}
| Humedad: {w_main['humidity']}%
| Presion Atmosferica: {w_main['pressure']}hPa
| Descripcion: {weather[0]['description']}
"""

    # Se borra el mensaje temporal en vez de editarlo
    # Esto es solo para poder editar el teclado
    # (edit_text no acepta el tipo ReplyKeyboardMarkup para reply_markup)
    await msg.delete()
    await update.message.reply_text(
        text=restext,
        reply_markup=main_menu_keyboard,
    )

    return Estado.MAIN_MENU


# </editor-fold>


# <editor-fold desc="[Utility Commands]">
async def cancel_command(update: Update, _) -> Estado:
    """Cancelar el ultimo comando."""
    await update.message.reply_text(
        text="Regresando al menu principal.",
        reply_markup=main_menu_keyboard,
    )
    return Estado.MAIN_MENU


async def cease_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Borrar todos los datos de usuario.
    yes, sin confirmacion.
    Usado para debug principalmente.
    """
    await update.message.reply_text(
        text="Borrando datos de usuario. Usa /start para comenzar de nuevo.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await limpiar_contadores(update, context)
    context.user_data.clear()

    return ConversationHandler.END


async def invalid_message(update: Update, _) -> None:
    """Cuando el usuario ingresa algo no valido, y preferimos informarle"""
    await update.message.reply_text(
        text=f"Bastante bien! Pero no entiendo ese mensaje.\n(/no para volver al menu principal)"
    )


# </editor-fold>


global config


# <editor-fold desc="[Main]">
def main() -> None:
    """Run the bot."""
    global config
    # Cargar tokens de config.toml
    try:
        config = toml.load("config.toml")
        # TODO: Checkear si los tokens son correctos?
        # Too much for 4 hours
    except FileNotFoundError:
        print("Archivo config.toml no encontrado.")
        exit(ENOENT)
    except TomlDecodeError | TypeError:
        print("Archivo config.toml invalido.")
        exit(EINVAL)

    # Crear el bot
    app = Application.builder() \
        .token(config['BOT_TOKEN']) \
        .persistence(PicklePersistence(filepath="userdata")) \
        .build()

    # Definir handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Estado.MAIN_MENU: [
                # Handler para iniciar el proceso de obtener el clima
                MessageHandler(
                    filters.Regex(re.compile(r'clima', re.IGNORECASE)), nuevo_clima
                ),

                # Handler para crear contadores
                MessageHandler(
                    filters.Regex(re.compile(r'conta(?:do)?r', re.IGNORECASE)), nuevo_contador
                ),
            ],
            Estado.CHOOSING_CITY: [
                # Handler para obtener el clima
                MessageHandler(
                    # Manejar todos los mensajes de texto que no sean comandos
                    filters.TEXT & ~filters.COMMAND, obtener_clima
                )
            ]
        },
        fallbacks=[
            CommandHandler("no", cancel_command),
            CommandHandler("cease", cease_command),
            MessageHandler(filters.ALL, invalid_message),
        ],
        name="main",
        persistent=True,
    )
    # Handler para actualizar contadores
    app.add_handler(CallbackQueryHandler(actualizar_contador, pattern=r'^C'))

    # Handler principal de la conversacion
    app.add_handler(conv_handler)

    # Correr bot
    app.run_polling()


if __name__ == "__main__":
    main()
# </editor-fold>
