from jinja2 import Template


USER_MESSAGE_TEMPLATE = Template('''
USER MESSAGE:
{% if from_ %}{{from_}} {% endif %}
{{datetime}}{% if text %}
{{text}}{% endif %}{% if sticker_emoji %}
К этому сообщению прикреплён стикер с эмодзи {{sticker_emoji}}{% endif %}{% if photo %}
К этому сообщению прикреплено фото{% endif %}{% if reply_to.text %}
(В ответ на сообщение "{{reply_to.text|truncate(100, true, '...')}}"{% if reply_to.from_ %} от {{reply_to.from_}}{% endif %}){% endif %}{% if reactions %}
Поставленные реакции: {% for reaction in reactions %}{{reaction.emoji}} ({{reaction.count}}) {% endfor %}{% endif %}
------------------------
''')


SERVICE_MESSAGE_TEMPLATE = Template('''
SERVICE MESSAGE:
{% if datetime %}{{datetime}} {% endif %}
{% if action %}action = {{action}} {% endif %}
{% if actor %}actor = {{actor}} {% endif %}
------------------------
''')
