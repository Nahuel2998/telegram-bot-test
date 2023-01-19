#!/usr/bin/env python

import logging
from errno import *

import re
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
CONTADOR = 'contador'
CONTADOR_MSG_ID = 'contador_msg_id'


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
        text="¡Hola! ¿Qué necesitas? 😊",
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


async def nuevo_contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Crear un nuevo contador."""
    veces_contadas = f"Veces contadas: {context.user_data.get(CONTADOR)}"

    # Si existe otro mensaje con un contador, eliminarle los botones
    # Posiblemente sea mejor eliminar el mensaje, pero hay un limite de 48h para ello
    # Siempre se puede editar, por eso he elegido esto
    if CONTADOR_MSG_ID in context.user_data.keys():
        chat_id, message_id = context.user_data[CONTADOR_MSG_ID]
        await update.get_bot().edit_message_text(
            text=veces_contadas,
            chat_id=chat_id,
            message_id=message_id,
        )

    context.user_data[CONTADOR_MSG_ID] = (
        update.message.chat_id,
        (await update.message.reply_text(
            text=veces_contadas,
            reply_markup=contador_keyboard,
        )).message_id,
    )


async def actualizar_contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actualizar un contador existente."""
    await update.callback_query.answer()

    if int(update.callback_query.data[1]):
        context.user_data[CONTADOR] += 1
    else:
        context.user_data[CONTADOR] = 0

    await update.callback_query.edit_message_text(
        text=f"Veces contadas: {context.user_data.get(CONTADOR)}",
        reply_markup=contador_keyboard,
    )
# </editor-fold>


# <editor-fold desc="[Utility Commands]">
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Estado:
    """Cancelar el ultimo comando."""
    await update.message.reply_text(
        text="Regresando al menu principal.",
        reply_markup=main_menu_keyboard,
    )
    return Estado.MAIN_MENU


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Borrar todos los datos de usuario.
    yes, sin confirmacion.
    Usado para debug principalmente.
    """
    await update.message.reply_text(
        text="Borrando datos de usuario. Usa /start para comenzar de nuevo.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()

    return ConversationHandler.END
# </editor-fold>


# <editor-fold desc="[Main]">
def main() -> None:
    """Run the bot."""
    # Cargar tokens de config.toml
    try:
        config = toml.load("config.toml")
        # TODO: Checkear si los tokens son correctos?
    except FileNotFoundError:
        print("Archivo config.toml no encontrado.")
        exit(ENOENT)
    except TomlDecodeError | TypeError:
        print("Archivo config.toml invalido.")
        exit(EINVAL)

    # Crear el bot
    application = Application.builder() \
        .token(config['BOT_TOKEN']) \
        .persistence(PicklePersistence(filepath="userdata")) \
        .build()

    # Definir handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Estado.MAIN_MENU: [
                # Handler para crear contadores
                MessageHandler(
                    filters.Regex(re.compile(r'conta(?:do)?r', re.IGNORECASE)), nuevo_contador
                ),

                # Handler para actualizar contadores
                CallbackQueryHandler(actualizar_contador, pattern=r'^C'),
            ],
        },
        fallbacks=[CommandHandler("no", cancel_command), CommandHandler("reset", reset_command)],
        name="main",
        persistent=True,
    )
    application.add_handler(conv_handler)

    # Correr bot
    application.run_polling()


if __name__ == "__main__":
    main()
# </editor-fold>
