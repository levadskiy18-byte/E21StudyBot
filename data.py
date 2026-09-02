# База данных предметов, преподавателей и ссылок
SUBJECTS = {
    "Українська мова та література": {
        "teacher": "Бречко Олена Миколаївна",
        "classroom": "https://classroom.google.com/c/ODc2NDI2NTM0NzYw?cjc=j7foncpe",
        "zoom": "https://us04web.zoom.us/j/5546658153?pwd=eUR0cnF2Y3pIUHozeHhjV09XOU9OQT09"
    },
    "Виховні години та фізичне виховання": {
        "teacher": "Шевченко Тетяна Валеріївна",
        "classroom": "https://classroom.google.com/c/ODAxMDU3MTA0Mzk5?cjc=p4c75e2n",
        "zoom": "https://us05web.zoom.us/j/87000857117?pwd=VXduMys0V3FhanJQY0VxdUU0QllwQT09"
    },
    "Фізика": {
        "teacher": "Табачник Олена Миколаївна",
        "classroom": "https://classroom.google.com/c/ODc2NTQ3Mjk0NTMx?cjc=42m7a3h6",
        "zoom": "https://us05web.zoom.us/j/5433319306?pwd=R1VQMFlHbFY3UGRSS0p0WC9OQnNyZz09"
    },
    "Конструкційні та електротехнічні матеріали": {
        "teacher": "Віктор Лиманченко",
        "classroom": "Код: zesv5q3",
        "zoom": "https://us05web.zoom.us/j/88667130665?pwd=ZU9aSTBENTJRUm84WDFLb1VyMFNvZz09"
    },
    "Історія 9 клас": {
        "teacher": "Не вказано",
        "classroom": "https://classroom.google.com/c/NzA0MjY1MDQxNDIx?cjc=dhdtbsa",
        "zoom": "https://us05web.zoom.us/j/82252074027?pwd=RUt5MzFUbUx3Q2FxcmcyK2xsM2lJdz09"
    },
    "Історія 11 клас": {
        "teacher": "Не вказано",
        "classroom": "https://classroom.google.com/c/NzA9NDI2NDk1Njg0?cjc=55cc5dj",
        "zoom": "https://us05web.zoom.us/j/82252074027?pwd=RUt5MzFUbUx3Q2FxcmcyK2xsM2lJdz09"
    },
    "Правознавство": {
        "teacher": "Мироненко Олена Юріївна",
        "classroom": "https://classroom.google.com/c/ODc2NjE5MTkyMjEy?cjc=o3ft4pfb",
        "zoom": "https://us05web.zoom.us/j/3321454583?pwd=WURKSlhUTGhDeFhEa09QU1Q4TmZkdz09"
    },
    "Англійська мова": {
        "teacher": "Салманова Лариса Миколаївна",
        "classroom": "https://classroom.google.com/c/ODY5MzQ0MDExNDk4?cjc=jwi4ysfh",
        "zoom": "https://us04web.zoom.us/j/74528114620?pwd=BEPbNFBlqrsf7BHIqisgHYim4kbQwT.1"
    },
    "Математика": {
        "teacher": "Гришко Галина Леонідівна",
        "classroom": "https://classroom.google.com/c/ODc2NjExMTIxOTc5?cjc=aff7yt24",
        "zoom": "https://us04web.zoom.us/j/79806870768?pwd=wscfwbeFgO4wbqmAxBJy4znUvOK5E0.1"
    },
    "Біологія і екологія": {
        "teacher": "Репринцева Ніна Іванівна",
        "classroom": "https://classroom.google.com/c/ODc2NjM0NDgyMjAy?cjc=pjsofk5y",
        "zoom": "https://us04web.zoom.us/j/4316219745?pwd=MvEw06btO8M1LQIg11moihensLlJ9V.1"
    }
}

# Расписание звонков (пары)
CALLS = {
    1: {"start": "08:00", "end": "09:20"},
    2: {"start": "09:30", "end": "10:50"},
    3: {"start": "11:10", "end": "12:30"},
    4: {"start": "12:40", "end": "14:00"}
}

# Пример расписания на неделю (его легко менять прямо здесь!)
SCHEDULE = {
    "Monday": {
        1: "Біологія і екологія",
        2: "Математика",
        3: "Українська мова та література"
    },
    "Tuesday": {
        1: "Фізика",
        2: "Англійська мова",
        3: "Правознавство"
    },
    "Wednesday": {
        1: "Історія 9 клас",
        2: "Конструкційні та електротехнічні матеріали"
    },
    "Thursday": {
        1: "Математика",
        2: "Фізика"
    },
    "Friday": {
        1: "Виховні години та фізичне виховання",
        2: "Історія 11 клас"
    }
}
