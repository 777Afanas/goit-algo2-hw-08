import random
from typing import Dict, Deque
import time
from collections import deque

# Клас для реалізації Rate Limiter за допомогою алгоритму Sliding Window Log.
class SlidingWindowRateLimiter:
    """
    Реалізація Rate Limiter з використанням алгоритму Sliding Window (з журналюванням).
    Обмежує кількість повідомлень (max_requests) у заданому часовому вікні (window_size).
    """
    # Конструктор класу.
    def __init__(self, window_size: int = 10, max_requests: int = 1):
        """
        Ініціалізація Rate Limiter.

        Args:
            window_size: Розмір часового вікна в секундах (за замовчуванням 10 сек).
            max_requests: Максимальна кількість запитів (повідомлень) у вікні (за замовчуванням 1).
        """
        # Зберігаємо розмір вікна (T) для перевірки обмеження.
        self.window_size = window_size
        # Зберігаємо максимальну кількість запитів (N) у межах вікна.
        self.max_requests = max_requests

        # Словник для зберігання історії повідомлень кожного користувача.
        # Ключ: user_id (str), Значення: Deque[float] (часові мітки повідомлень).
        # Deque (двостороння черга) дозволяє швидко видаляти елементи з обох кінців (O(1)).
        self.request_history: Dict[str, Deque[float]] = {}

    # Метод для очищення застарілих часових міток із вікна.
    def _cleanup_window(self, user_id: str, current_time: float) -> None:
        """
        Очищає застарілі запити з вікна користувача, які вийшли за межі [current_time - window_size, current_time].
        """
        # Якщо користувача немає в історії, нічого не робимо.
        if user_id not in self.request_history:
            return

        # Отримуємо Deque з часовими мітками для поточного користувача.
        user_timestamps = self.request_history[user_id]
        
        # Цикл видалення найстаріших міток часу (з лівого боку Deque),
        # які вийшли за межі активного вікна.
        # Умова: timestamp <= current_time - self.window_size.
        while user_timestamps and user_timestamps[0] <= current_time - self.window_size:
            # Видаляємо найстаріший елемент.
            user_timestamps.popleft()

        # Вимога 3: Якщо після очищення Deque порожня, видаляємо запис про користувача.
        if not user_timestamps:
            del self.request_history[user_id]

    # Метод для перевірки можливості відправлення повідомлення.
    def can_send_message(self, user_id: str) -> bool:
        """
        Перевіряє, чи дозволено користувачеві відправити повідомлення в цей момент.
        """
        # Отримуємо поточний час для визначення меж вікна.
        current_time = time.perf_counter()
        
        # Очищаємо вікно від застарілих запитів перед перевіркою ліміту.
        self._cleanup_window(user_id, current_time)

        # Вимога 2: Якщо користувач не має історії (перше повідомлення), дозволяємо.
        # Це також включає випадок, коли вся історія була щойно очищена.
        if user_id not in self.request_history or not self.request_history[user_id]:
            return True

        # Перевіряємо, чи кількість повідомлень у поточному вікні не перевищує ліміт.
        # Якщо len < max_requests, повідомлення дозволено.
        # Вимога 1: Для max_requests=1, якщо вже є 1 повідомлення, повертається False.
        return len(self.request_history[user_id]) < self.max_requests

    # Метод для запису нового повідомлення та оновлення історії.
    def record_message(self, user_id: str) -> bool:
        """
        Спроба записати нову часову мітку повідомлення.
        Повертає True, якщо запис дозволено і зроблено, False — інакше.
        """
        # Спочатку перевіряємо, чи дозволено відправлення повідомлення.
        if not self.can_send_message(user_id):
            return False

        # Отримуємо поточний час як часову мітку для нового повідомлення.
        current_time = time.perf_counter()

        # Ініціалізуємо Deque, якщо запис про користувача відсутній.
        if user_id not in self.request_history:
            self.request_history[user_id] = deque()

        # Додаємо нову часову мітку до правого кінця Deque.
        self.request_history[user_id].append(current_time)
        return True

    # Метод для розрахунку часу очікування до наступного дозволеного повідомлення.
    def time_until_next_allowed(self, user_id: str) -> float:
        """
        Вимога 4: Розраховує час очікування (у секундах) до можливості відправлення наступного повідомлення.
        """
        # Якщо користувач не має історії, час очікування = 0.
        if user_id not in self.request_history:
            return 0.0

        # Отримуємо поточний час.
        current_time = time.perf_counter()
        # Очищаємо вікно, щоб отримати актуальну кількість повідомлень.
        self._cleanup_window(user_id, current_time)

        # Якщо після очищення історія порожня, повідомлення дозволено, очікування = 0.
        if not self.request_history[user_id]:
            return 0.0

        # Якщо кількість повідомлень у вікні менша за ліміт, повідомлення дозволено, очікування = 0.
        if len(self.request_history[user_id]) < self.max_requests:
            return 0.0
            
        # Якщо ліміт вичерпано, час очікування визначається найстарішим повідомленням.
        # Часова мітка найстарішого запиту знаходиться зліва.
        oldest_timestamp = self.request_history[user_id][0]
        
        # Обчислюємо час, коли найстаріше повідомлення покине вікно: oldest_timestamp + window_size.
        time_to_allow = oldest_timestamp + self.window_size
        
        # Час, що залишився до цього моменту.
        time_to_wait = time_to_allow - current_time
        
        # Повертаємо час очікування, мінімум 0.0.
        return max(0.0, time_to_wait)


# Демонстрація роботи
def test_rate_limiter():
    # Створюємо rate limiter: вікно 10 секунд, 1 повідомлення
    limiter = SlidingWindowRateLimiter(window_size=10, max_requests=1)

    # Симулюємо потік повідомлень від користувачів (послідовні ID від 1 до 20)
    print("\n=== Симуляція потоку повідомлень ===")
    
    for message_id in range(1, 11):
        # Симулюємо різних користувачів (ID від 1 до 5)
        user_id = message_id % 5 + 1

        # Спроба записати повідомлення.
        result = limiter.record_message(str(user_id))
        # Розрахунок часу очікування, якщо повідомлення було відхилено.
        wait_time = limiter.time_until_next_allowed(str(user_id))

        print(f"Повідомлення {message_id:2d} | Користувач {user_id} | "
              f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}")

        # Невелика затримка між повідомленнями для реалістичності
        # Випадкова затримка від 0.1 до 1 секунди
        time.sleep(random.uniform(0.1, 1.0))

    # Чекаємо 4 секунди
    print("\nОчікуємо 4 секунди...")
    time.sleep(4)

    print("\n=== Нова серія повідомлень після очікування ===")
    for message_id in range(11, 21):
        user_id = message_id % 5 + 1
        # Спроба записати повідомлення.
        result = limiter.record_message(str(user_id))
        # Розрахунок часу очікування.
        wait_time = limiter.time_until_next_allowed(str(user_id))
        
        print(f"Повідомлення {message_id:2d} | Користувач {user_id} | "
              f"{'✓' if result else f'× (очікування {wait_time:.1f}с)'}")
        # Випадкова затримка від 0.1 до 1 секунди
        time.sleep(random.uniform(0.1, 1.0))

# Запуск тестової функції при виконанні скрипта.
if __name__ == "__main__":
    test_rate_limiter()