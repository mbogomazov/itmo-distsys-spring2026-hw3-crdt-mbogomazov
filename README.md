# Домашнее задание 3: CRDT (Conflict-free Replicated Data Types)

## Обязательно напишите ФИО в свой PR!!!

## Введение

Это домашнее задание посвящено реализации **CRDT (Conflict-free Replicated Data Types)** — специальных структур данных, которые позволяют нескольким репликам в распределённой системе автоматически сходиться к одному и тому же состоянию без необходимости координации (консенсуса).

### Основные концепции

**CRDT** — это тип структуры данных, которая:
- Может быть обновлена независимо на разных узлах без синхронизации
- Гарантирует **консистентность** (eventual consistency) — все реплики рано или поздно сходятся к одному состоянию
- Не требует центрального координатора для разрешения конфликтов

### Два подхода к CRDT

#### 1. **State-based CvRDT (Convergent Replicated Data Type)**
- Логика: синхронизируются **полные состояния** между репликами
- Требование: операция слияния (`merge`) должна быть **коммутативна, ассоциативна и идемпотентна**
- Применение: когда передача полного состояния экономнее, чем операций

#### 2. **Operation-based CmRDT (Commutative Replicated Data Type)**
- Логика: синхронизируются **операции**, а не состояния
- Требование: все операции должны быть **коммутативны** (порядок выполнения не важен)
- Применение: когда операции мелкие, но состояние большое

---

## Задание

Вам нужно реализовать **9 различных CRDT** с полной поддержкой операций и слияния.

### Структура решения

```
src/
├── __init__.py
├── crdt_base.py           # Базовые классы и интерфейсы
├── registers.py           # LWW-Register, MV-Register
├── sets.py                # Grow-only Set, PN-Set, Unique-Set, OR-Set
├── counters.py            # Grow-only Counter, PN-Counter
└── graph.py               # Add-only DAG

tests/
├── test_registers.py
├── test_sets.py
├── test_counters.py
├── test_graph.py
└── test_properties.py     # Property-based tests (коммутативность, идемпотентность)
```

---

## Описание каждого CRDT

### 1. LWW-Register (Last-Writer-Wins Register)
**Тип:** State-based CvRDT

**Описание:** Регистр, который хранит последнее записанное значение, используя временные метки. При конфликте побеждает запись с более поздней временной меткой (или с наибольшим уникальным ID).

**API:**
```python
class LWWRegister:
    def write(self, value: Any, timestamp: float) -> None
    def read() -> Any
    def merge(other: 'LWWRegister') -> None
```

**Свойства:**
- Каждое значение имеет привязанную временную метку
- При слиянии выбирается значение с максимальной временной меткой
- Должен быть идемпотентен к повторным слияниям

---

### 2. MV-Register (Multi-Value Register)
**Тип:** State-based CvRDT

**Описание:** Регистр, который может хранить **множество значений** в случае конфликтующих записей. Разрешение конфликтов передаётся пользователю.

**API:**
```python
class MVRegister:
    def write(self, value: Any) -> None
    def read() -> Set[Any]      # Может вернуть несколько значений
    def merge(other: 'MVRegister') -> None
```

**Свойства:**
- Использует **version vectors** для отслеживания причинной истории
- Когда есть конфликт (несравнимые версии), хранит оба значения
- После слияния несравнимых веток показывает оба значения

---

### 3. Grow-only Set
**Тип:** State-based CvRDT

**Описание:** Множество, которое **только растёт**. Удаление элементов запрещено.

**API:**
```python
class GrowOnlySet:
    def add(self, element: Any) -> None
    def contains(self, element: Any) -> bool
    def elements() -> Set[Any]
    def merge(other: 'GrowOnlySet') -> None
```

**Свойства:**
- Операция добавления идемпотентна (добавление одного элемента дважды = добавление один раз)
- Слияние = объединение всех элементов
- Простейший CRDT

---

### 4. PN-Set (Positive-Negative Set)
**Тип:** State-based CvRDT

**Описание:** Множество, которое поддерживает как **добавление**, так и **удаление** элементов. Использует уникальные уникальные ID (uid) для отслеживания операций.

**API:**
```python
class PNSet:
    def add(self, element: Any, uid: str) -> None
    def remove(self, element: Any, uid: str) -> None
    def contains(self, element: Any) -> bool
    def elements() -> Set[Any]
    def merge(other: 'PNSet') -> None
```

**Внутренняя репрезентация:**
- Хранит множество добавлений: `{(элемент, uid_добавления)}`
- Хранит множество удалений: `{(элемент, uid_добавления)}`
- Элемент есть в множестве, если uid его добавления существует, но не существует в удалениях

**Проблема:** Если удалить элемент после добавления, а потом переклассифицировать, он должен остаться удалённым.

---

### 5. Unique-Set (OR-Set Simplified)
**Тип:** State-based CvRDT

**Описание:** Множество с уникальными тегами для каждого добавления. Упрощённая версия OR-Set.

**API:**
```python
class UniqueSet:
    def add(self, element: Any) -> str         # Возвращает уникальный uid
    def remove(self, element: Any, uid: str) -> None
    def contains(self, element: Any) -> bool
    def elements() -> Set[Any]
    def merge(other: 'UniqueSet') -> None
```

**Внутренняя репрезентация:**
- Каждое добавление имеет уникальный tag (uuid или счётчик)
- Хранит: `{(элемент, tag_1), (элемент, tag_2), ...}`
- Удаление удаляет конкретный tag
- Элемент есть в множестве, если есть хотя бы один его tag

---

### 6. Observed-Remove Set (OR-Set)
**Тип:** State-based CvRDT

**Описание:** Множество, которое полностью поддерживает добавление и удаление без аномалий. Использует версионные векторы и валидировать удаления таким образом, чтобы они не удаляли "наблюдаемое" добавление.

**API:**
```python
class ORSet:
    def add(self, element: Any) -> str         # Возвращает uid добавления
    def remove(self, element: Any, uid: str) -> None
    def contains(self, element: Any) -> bool
    def elements() -> Set[Any]
    def merge(other: 'ORSet') -> None
```

**Свойства:**
- Не может быть "вскрыт" добавлениями после удаления
- Использует каузальные отношения для валидации
- Если реплика A добавила элемент, реплика B удалила, то другая реплика C видит обновления обеих A и B

---

### 7. Grow-only Counter
**Тип:** State-based CvRDT

**Описание:** Счётчик, который **только увеличивается**. Каждая реплика имеет собственный локальный счётчик.

**API:**
```python
class GrowOnlyCounter:
    def increment(self, replica_id: str, value: int = 1) -> None
    def value() -> int                          # Сумма всех реплик
    def merge(other: 'GrowOnlyCounter') -> None
```

**Внутренняя репрезентация:**
- Вектор: `{replica_id_1: count_1, replica_id_2: count_2, ...}`
- `value()` = сумма всех значений в векторе

---

### 8. PN-Counter (Positive-Negative Counter)
**Тип:** State-based CvRDT

**Описание:** Счётчик, который поддерживает как **инкремент**, так и **декремент**. Использует два grow-only счётчика.

**API:**
```python
class PNCounter:
    def increment(self, replica_id: str, value: int = 1) -> None
    def decrement(self, replica_id: str, value: int = 1) -> None
    def value() -> int
    def merge(other: 'PNCounter') -> None
```

**Внутренняя репрезентация:**
- Хранит два grow-only счётчика: P (положительный) и N (отрицательный)
- `value()` = P.value() - N.value()

---

### 9. Add-only Monotonic Acyclic Graph
**Тип:** State-based CvRDT

**Описание:** Граф, к которому можно только **добавлять** рёбра. Граф должен оставаться ациклическим (no cycles).

**API:**
```python
class AddOnlyDAG:
    def add_edge(self, from_node: Any, to_node: Any) -> bool  # False если создаст цикл
    def add_node(self, node: Any) -> None
    def has_edge(self, from_node: Any, to_node: Any) -> bool
    def nodes() -> Set[Any]
    def edges() -> Set[Tuple[Any, Any]]
    def merge(other: 'AddOnlyDAG') -> None
```

**Свойства:**
- Добавление рёбер, которые создают цикл, должно быть отклонено
- Слияние объединяет все узлы и рёбра обоих графов
- Должна быть проверка ацикличности (можно использовать DFS или топологическую сортировку)

---

## Рекомендации по реализации

### Виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate
./.venv/bin/pip install -r requirements.txt

# запустить тесты
./.venv/bin/python -m pytest
```

### Полезные техники:

1. **Глубокое копирование для тестов:**
   ```python
   from copy import deepcopy
   s1_copy = deepcopy(s1)
   ```

2. **Для PN-Set и OR-Set: используйте UUID для уникальных ID:**
   ```python
   from uuid import uuid4
   uid = str(uuid4())
   ```

3. **Для версионных векторов:**
   ```python
   # Version vector как словарь {replica_id: counter}
   vv = {'replica_1': 5, 'replica_2': 3}
   ```

---

## Критерии оценки

| Критерий | Баллы |
|----------|-------|
| Счетчики | 2 |
| Регистры | 2 |
| Множества | 4 |
| Графы | 2 |
| **Итого** | **10** |

---
