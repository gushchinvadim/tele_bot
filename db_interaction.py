from db_conn import get_db_connection


def initialize_db():
    """Создаёт таблицы в базе данных и заполняет их начальными данными."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Таблица пользователей
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL  PRIMARY KEY,
                user_id    BIGINT UNIQUE NOT NULL,
                username   VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Общий словарь
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL      PRIMARY KEY,
                    target_word    VARCHAR(255) UNIQUE NOT NULL,
                    translate_word VARCHAR(255) NOT NULL
                )
                """)

            # Персональный словарь
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_words (
                id SERIAL      PRIMARY KEY,
                user_id        BIGINT       NOT NULL REFERENCES users (user_id),
                target_word    VARCHAR(255) NOT NULL,
                translate_word VARCHAR(255) NOT NULL,
                UNIQUE (user_id, target_word)
            )
            """)

            conn.commit()


def ensure_user_exists(user_id, username):
    """Проверяет, существует ли пользователь в базе данных и создает его, если необходимо."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO users (user_id, username)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE 
            SET username = EXCLUDED.username
            """, (user_id, username))
            conn.commit()


def fill_common_words_table(common_words):
    """Заполняет общий словарь."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
            INSERT INTO words (target_word, translate_word)
            VALUES (%s, %s)
            ON CONFLICT (target_word) DO NOTHING
            """, common_words)
            conn.commit()


def get_random_words(cid, limit=4):
    """Получает случайные слова из общего и персонального словарей."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT target_word, translate_word
              FROM (
                SELECT w.target_word, w.translate_word
                  FROM words w
                 UNION 
                SELECT uw.target_word, uw.translate_word
                  FROM user_words uw
                 WHERE uw.user_id = %s
                  ) AS combined_words
                 ORDER BY RANDOM()
                 LIMIT %s;
            """, (cid, limit))
            return cur.fetchall()


def check_word_existence(word):
    """Проверяет, существует ли слово в общем словаре."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                  FROM words
                 WHERE target_word = %s
            """, (word,))
            return cur.fetchone() is not None


def add_word_to_user(user_id, target_word, translation):
    """Сохраняет слово в персональный словарь."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO user_words (user_id, target_word, translate_word)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, target_word) DO NOTHING
            """, (user_id, target_word.strip().capitalize(), translation.strip().capitalize()))
            conn.commit()


def delete_user_word(user_id, word_to_delete):
    """Удаляет слово из персонального словаря."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM user_words
                 WHERE user_id = %s
                   AND target_word = %s
             RETURNING target_word;
            """, (user_id, word_to_delete))
            result = cur.fetchone()
            conn.commit()
            return result


def update_word_to_user_dict(user_id, target_word, translate_word):
    """Обновляет персональный словарь."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO user_words (user_id, target_word, translate_word)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, target_word) DO NOTHING
            """, (user_id, target_word, translate_word))
            conn.commit()