@router.message(F.text == 'Выбрать напарника')
async def set_position(message: Message, state: FSMContext):
    room: Room = await get_room_by(message=message)
    player: Player = await get_player_by(message=message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not room.characters_united:
        await message.answer(
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    if not room.availible_players:
        await message.answer('Свободных игроков больше нет')
        return None

    if len(room.players) == 1:
        await message.answer(
            text=(
                'Вы играете в одиночку и поэтому '
                'можете быть напарником только самому себе'
            ),
            reply_markup=kb.start_round_keyboard
        )
        player.guesser = player
        player.riddler = player
        room.players_ready = True
        room.current_player = player
        return None

    await message.answer(
        text='Выберите напарника',
        reply_markup=await kb.inline_guessers(
            room_players=room.availible_players,
            current_player=player
        )
    )
    # await state.set_state(Reg.position)


@router.message(Reg.position)
async def add_position(message: Message, state: FSMContext):
    await state.clear()
    room: Room = await get_room_by(message=message)
    player: Player = await get_player_by(message=message)
    result = room.check_position(message)

    if message.text == '/exit':
        await remove_player_by(message=message)
        return None

    if result == player.Messages.OK:
        player.set_position(message)
        room.set_players_position(player)
        await message.answer(
            text=player.Messages.READY_TO_PLAY,
            reply_markup=kb.play_keyboard
        )
        return None

    await message.answer(
        text=result,
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        text=(
            'Доступные номера: '
            f'{room.availible_positions}'
        )
    )
    await state.set_state(Reg.position)