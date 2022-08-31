from vkbottle import Keyboard, KeyboardButtonColor, Callback

def create_keyboard(array : list, inraw_count : int = 2, Color : KeyboardButtonColor = KeyboardButtonColor.POSITIVE) -> Keyboard:
	KEYBOARD = Keyboard(one_time=True, inline=False)
	for index, text in enumerate (array):
		if (index+1) % inraw_count != 0 and index:
			KEYBOARD.row()
		KEYBOARD.add(Callback(label=text, payload={"cmd": text}), color=Color)
	KEYBOARD.get_json()
	return KEYBOARD



