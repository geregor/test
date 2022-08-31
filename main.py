import json
import asyncio
import time
from vkbottle.dispatch.rules.base import CommandRule
from vkbottle.bot import Bot , Message
from sett import token
from typing import Tuple  # Нада
from vkbottle import VKAPIError , BaseStateGroup , CtxStorage , GroupEventType , PhotoMessageUploader, EMPTY_KEYBOARD
from keyboard import create_keyboard
from file_for_text import QUESTIONS
import re

bot = Bot ( token=token )  # Свой токен
prefix = [ "!" ]  # С чего начинается команда


def read_file ( path: str ):
	with open ( path , 'r' ) as f:
		data: dict = json.load ( f )
	return data


def write_file ( path: str , data: dict ):
	with open ( path , 'w' ) as f:
		json.dump ( data , f , ensure_ascii=False , indent=4 )

@bot.on.private_message ( CommandRule ( "вопрос добавить" , prefix , 1 , sep=str ( time.time ( ) ) ) )
async def add_quiz ( message: Message , args: Tuple [ str ] ):
	try:
		item = args [ 0 ]
		data = read_file ( 'data.json' )
		# Проверка на совпадение
		for index , each in enumerate ( list ( data.values ( ) ) ):
			if item in each [ 'question' ]:
				await message.answer ( f"Данный вопрос уже есть базе данных под id {index + 1}" )
				return
		# Проверяем целосность ID, что бы если удалили один, то он заменился добавленным
		arr = list ( data.keys ( ) )
		last_key = 0
		for i in arr:
			if int ( i ) > last_key: last_key = int ( i )
		ID = False
		for key in range ( 1 , last_key + 1 ):
			if str ( key ) not in arr:
				ID = key
				break
		if not ID:
			ID = len ( data ) + 1
		# Добавляем в БД новый вопрос
		data.update ( { ID: { "question": item , "answer": None } } )
		write_file ( 'data.json' , data )
		await message.answer ( f"Вопрос добавлен в базу данных под id {ID}" )
	except VKAPIError as e:
		print ( "Возникла ошибка [1]" , e.code )


@bot.on.private_message ( CommandRule ( "вопрос удалить" , prefix , 1 , sep=str ( time.time ( ) ) ) )
async def remove_quiz ( message: Message , args: Tuple [ str ] ):
	try:
		id = args [ 0 ]
		data = read_file ( 'data.json' )
		# Проверка на id
		if id not in data:
			await message.answer ( f"Вопроса с данным id в базе данных не найдено" )
			return
		del data [ id ]
		write_file ( 'data.json' , data )
		await message.answer ( f"Вопрос с данным id был успешно удален" )
	except VKAPIError as e:
		print ( "Возникла ошибка [2]" , e.code )


@bot.on.private_message ( CommandRule ( "вопрос показать" , prefix , 1 , sep=str ( time.time ( ) ) ) )
async def show_quiz ( message: Message , args: Tuple [ str ] ):
	try:
		id = args [ 0 ]
		data = read_file ( 'data.json' )
		# Проверка на id
		if id not in data:
			await message.answer ( f"Вопроса с данным id в базе данных не найдено" )
			return
		info = data [ id ]
		await message.answer ( f"Вопрос: {info [ 'question' ]}\n"
		                       f"Ответ: {info [ 'answer' ]}" )
	except VKAPIError as e:
		print ( "Возникла ошибка [3]" , e.code )


@bot.on.private_message ( CommandRule ( "ответ" , prefix , 1 , sep=str ( time.time ( ) ) ) )
async def show_quiz ( message: Message , args: Tuple [ str ] ):
	try:
		args = args [ 0 ]
		args = args.split ( maxsplit=1 )
		id , answer = args [ 0 ] , args [ 1 ]
		data = read_file ( 'data.json' )
		# Проверка на id
		if id not in data:
			await message.answer ( f"Вопроса с данным id в базе данных не найдено" )
			return
		# Добавляем в БД новый вопрос
		data.update ( { id: { "question": data [ id ] [ 'question' ] , "answer": answer } } )
		write_file ( 'data.json' , data )
		await message.answer ( f"Ответ добавлен в базу данных под id {id}" )
	except VKAPIError as e:
		print ( "Возникла ошибка [4]" , e.code )


class QT ( BaseStateGroup ):
	FirstStep = "2"
	SecondStep = "3"
	ThirdStep = "4"
	FourthStep = "5"
	FifthStep = "6"
	NotIncluded = None  # Это что бы не ломалось ничего


class Question ( BaseStateGroup ):
	CreateQuestion = "CreateQuestion"


QT_Arr = [ QT.FirstStep , QT.SecondStep , QT.ThirdStep , QT.FourthStep , QT.FifthStep , QT.NotIncluded ]
# ctx будет нужен для сохранения ответов.
ctx = CtxStorage ( )


@bot.on.private_message ( CommandRule ( "задать вопрос" , prefix , 0 ) )
async def ask_question ( message: Message ):
	try:
		global keyboard_text
		global step
		global Info
		step = 0
		keyboard_text = [ ]
		text = f"На какую тему вы хотите задать вопрос?\n"
		for ind , question in enumerate ( QUESTIONS ):
			text += f"{ind + 1}) {question [ 'name' ]}\n"
			keyboard_text.append ( question [ 'name' ] )
		await bot.state_dispenser.set ( message.peer_id , QT_Arr [ step ] )
		Info = await message.answer ( text , keyboard=create_keyboard ( keyboard_text ) )
	except VKAPIError as e:
		print ( "Возникла ошибка [6]" , e.code )


# Обработчик диалога
@bot.on.raw_event ( GroupEventType.MESSAGE_EVENT )
async def MessageTree ( message: Message ):
	try:
		await bot.api.messages.send_message_event_answer (
			event_id=message [ 'object' ] [ 'event_id' ] ,
			peer_id=message [ 'object' ] [ 'peer_id' ] ,
			user_id=message [ 'object' ] [ 'user_id' ]
		)
		messageText = message [ 'object' ] [ 'payload' ] [ 'cmd' ]
		# ----------------------------------------
		global Info
		global keyboard_text
		print ( keyboard_text )
		answer = [ [ i , x ] for i , x in enumerate ( keyboard_text ) if x == messageText ]
		if answer [ 0 ] [ 1 ] == 'Здесь нет моего варианта':
			await bot.state_dispenser.set ( message [ 'object' ] [ 'peer_id' ] , Question.CreateQuestion )
			await bot.api.messages.send ( peer_id=message [ 'object' ] [ 'peer_id' ] ,
			                              message="Опишите свою проблему или задайте вопрос" , random_id=0 )
			return
		answer = answer [ 0 ]

		if answer == [ ]:
			await bot.api.messages.send ( message="Я вас не понял!" , peer_id=Info.peer_id , random_id=0 )
			return
		# Смотрим есть ли продолжение для диалога
		global step
		if step == 0:
			TestArr = QUESTIONS [ answer [ 0 ] ]
		else:
			TestArr = QUESTIONS [ ctx.get ( 0 ) ]
		for i in range ( step ):
			if i == step - 1:
				TestArr = TestArr [ QT_Arr [ i ].value ] [ "choices" ] [ answer [ 0 ] ]
			else:
				TestArr = TestArr [ QT_Arr [ i ].value ] [ "choices" ] [ ctx.get ( i + 1 ) ]
		ctx.set ( step , answer [ 0 ] )

		if QT_Arr [ step ].value in list ( TestArr.keys ( ) ):
			keyboard_text = []
			await bot.state_dispenser.set ( Info.peer_id , QT_Arr [ step ] )
			text = f"{TestArr [ QT_Arr [ step ].value ] [ 'text' ]}\n"
			for ind , question in enumerate ( TestArr [ QT_Arr [ step ].value ] [ "choices" ] ):
				text += f"{ind + 1}) {question [ 'name' ]}\n"
				keyboard_text.append ( question [ 'name' ] )
			await bot.api.messages.edit ( peer_id=Info.peer_id , message=text , message_id=Info.message_id ,
			                              keyboard=create_keyboard ( keyboard_text ) )
		elif "attachment" in list ( TestArr.keys ( ) ):
			photo_uploader = PhotoMessageUploader ( bot.api )
			attachment = await photo_uploader.upload ( TestArr['attachment'] )
			if "answer" in list ( TestArr.keys ( ) ):
				await bot.api.messages.edit ( peer_id=Info.peer_id , message=TestArr [ "answer" ] ,
				                              message_id=Info.message_id , attachment=attachment, keyboard=EMPTY_KEYBOARD )
			else:
				await bot.api.messages.edit ( peer_id=Info.peer_id , message="Смотри фото" ,
				                              message_id=Info.message_id , attachment=attachment, keyboard=EMPTY_KEYBOARD )
		else:
			await bot.api.messages.edit ( peer_id=Info.peer_id , message=TestArr [ "answer" ] ,
			                              message_id=Info.message_id,keyboard=EMPTY_KEYBOARD)
		step += 1
	except VKAPIError as e:
		print ( "Возникла ошибка [7]" , e.code )


# Создает и отправляет вопрос пользователя
@bot.on.private_message ( state=Question.CreateQuestion )
async def MessageTree ( message: Message ):
	try:
		print ( "I'm here" )
		_ID = 255117463  # 388438756
		forward = { "peer_id": message.peer_id , "conversation_message_ids": [ message.conversation_message_id ] }
		forward = json.dumps ( forward )
		users_info = await bot.api.users.get ( message.from_id )
		await bot.api.messages.send ( user_id=_ID , forward=forward , random_id=0 ,
		                              message=f"Был задан вопрос от {users_info [ 0 ].first_name} {users_info [ 0 ].last_name}" )
		send_user = await bot.api.users.get ( _ID )
		await message.answer (
			f"Ваш вопрос был отправлен админу {send_user [ 0 ].first_name} {send_user [ 0 ].last_name}" )
	except VKAPIError as e:
		print ( "Возникла ошибка [8]" , e.code )


asyncio.run ( bot.run_polling ( ) )
