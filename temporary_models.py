# Temporary


class Section:
    def __init__(self, id):
        self.id = id
        self.guid = id
        self.title = f'Название темы номер {id}'
        self.description = f'Описание темы номер {id}'


class Question:
    def __init__(self, id):
        self.id = id
        self.guid = id
        self.question_text = f'Текст вопроса {id}'
