import uuid

import allure
import pytest


def extract_item_id_from_create_response(response):
    response_json = response.json()
    assert isinstance(response_json, dict), "Create response must be an object"

    direct_id = response_json.get("id")
    if direct_id:
        return direct_id

    status_text = response_json.get("status", "")
    assert isinstance(status_text, str) and status_text, "Create response must contain id or status"

    for chunk in status_text.split():
        try:
            return str(uuid.UUID(chunk))
        except ValueError:
            continue

    raise AssertionError("Could not extract item id from create response: {0}".format(response.text))


def assert_error_response(response):
    assert response.status_code in (400, 404), response.text
    assert response.text, "Expected error payload to be non-empty"


def assert_item_shape(item):
    assert isinstance(item, dict), "Item must be an object"
    assert item.get("id"), "Item id is missing"
    assert isinstance(item.get("sellerId"), int), "sellerId must be integer"
    assert isinstance(item.get("name"), str) and item["name"], "name must be non-empty string"
    assert isinstance(item.get("price"), int), "price must be integer"
    assert isinstance(item.get("createdAt"), str) and item["createdAt"], "createdAt must be string"

    statistics = item.get("statistics")
    assert isinstance(statistics, dict), "statistics must be object"
    for field_name in ("likes", "viewCount", "contacts"):
        assert isinstance(statistics.get(field_name), int), "{0} must be integer".format(field_name)


def assert_statistics_shape(statistics_response):
    assert isinstance(statistics_response, list), "Statistics response must be a list"
    assert statistics_response, "Statistics response must not be empty"
    for statistics in statistics_response:
        assert isinstance(statistics, dict), "Statistics item must be an object"
        for field_name in ("likes", "viewCount", "contacts"):
            assert isinstance(statistics.get(field_name), int), "{0} must be integer".format(
                field_name
            )


def make_unknown_uuid():
    return str(uuid.uuid4())


@allure.epic("Avito internship API")
@allure.feature("POST /api/1/item")
@allure.story("Создание объявления")
@allure.title("Создание объявления с валидным payload")
@allure.description("Проверка успешного создания объявления и доступности созданной записи по id.")
@pytest.mark.smoke
def test_create_item_returns_full_created_entity(api_client, item_payload_factory):
    payload = item_payload_factory()

    with allure.step("Создать объявление"):
        response = api_client.create_item(payload)

    with allure.step("Проверить HTTP-статус и извлечь id созданного объявления"):
        assert response.status_code == 200, response.text
        created_item_id = extract_item_id_from_create_response(response)
        assert created_item_id

    with allure.step("Проверить, что созданное объявление доступно по id и содержит корректные данные"):
        get_response = api_client.get_item(created_item_id)
        assert get_response.status_code == 200, get_response.text
        items = get_response.json()
        assert isinstance(items, list), "GET item response must be a list"
        assert len(items) == 1, "Expected exactly one item in GET by id response"
        item = items[0]
        assert_item_shape(item)
        assert item["id"] == created_item_id
        assert item["sellerId"] == payload["sellerID"]
        assert item["name"] == payload["name"]
        assert item["price"] == payload["price"]
        assert item["statistics"] == payload["statistics"]


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/item/{id}")
@allure.story("Получение объявления по id")
@allure.title("Получение созданного объявления по id")
@allure.description("Проверка чтения объявления по идентификатору после успешного создания.")
@pytest.mark.smoke
@pytest.mark.e2e
def test_created_item_can_be_fetched_by_id(api_client, item_payload_factory):
    payload = item_payload_factory()

    with allure.step("Создать объявление"):
        create_response = api_client.create_item(payload)
        assert create_response.status_code == 200, create_response.text
        created_item_id = extract_item_id_from_create_response(create_response)

    with allure.step("Получить объявление по id"):
        get_response = api_client.get_item(created_item_id)

    with allure.step("Проверить, что объявление найдено и соответствует отправленным данным"):
        assert get_response.status_code == 200, get_response.text
        items = get_response.json()
        assert isinstance(items, list), "GET item response must be a list"
        assert len(items) == 1, "Expected exactly one item in GET by id response"
        actual_item = items[0]
        assert_item_shape(actual_item)
        assert actual_item["id"] == created_item_id
        assert actual_item["sellerId"] == payload["sellerID"]
        assert actual_item["statistics"] == payload["statistics"]


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/{sellerID}/item")
@allure.story("Получение всех объявлений продавца")
@allure.title("Получение списка объявлений конкретного продавца")
@allure.description("Проверка, что ручка возвращает только объявления указанного sellerID.")
@pytest.mark.smoke
@pytest.mark.e2e
def test_seller_items_endpoint_returns_only_requested_seller_items(api_client, item_payload_factory):
    payload_first = item_payload_factory(name="Seller item A")
    payload_second = item_payload_factory(name="Seller item B")
    another_payload = dict(item_payload_factory(name="Foreign seller item"))
    another_payload["sellerID"] = payload_first["sellerID"] + 1

    with allure.step("Создать два объявления одного продавца и одно чужое"):
        first_item = api_client.create_item(payload_first)
        second_item = api_client.create_item(payload_second)
        foreign_item = api_client.create_item(another_payload)
        assert first_item.status_code == 200, first_item.text
        assert second_item.status_code == 200, second_item.text
        assert foreign_item.status_code == 200, foreign_item.text
        first_id = extract_item_id_from_create_response(first_item)
        second_id = extract_item_id_from_create_response(second_item)
        foreign_id = extract_item_id_from_create_response(foreign_item)

    with allure.step("Запросить список объявлений продавца"):
        response = api_client.get_seller_items(payload_first["sellerID"])

    with allure.step("Проверить, что в выдаче есть нужные объявления и нет чужих"):
        assert response.status_code == 200, response.text
        items = response.json()
        assert isinstance(items, list), "Seller items response must be a list"
        returned_ids = set()
        for item in items:
            assert_item_shape(item)
            assert item["sellerId"] == payload_first["sellerID"]
            returned_ids.add(item["id"])

        assert first_id in returned_ids
        assert second_id in returned_ids
        assert foreign_id not in returned_ids


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/statistic/{id}")
@allure.story("Получение статистики по объявлению")
@allure.title("Получение статистики по созданному объявлению")
@allure.description("Проверка, что статистика доступна по id и согласована с данными объявления.")
@pytest.mark.smoke
@pytest.mark.e2e
def test_statistics_endpoint_returns_created_item_statistics(api_client, item_payload_factory):
    payload = item_payload_factory()

    with allure.step("Создать объявление"):
        create_response = api_client.create_item(payload)
        assert create_response.status_code == 200, create_response.text
        created_item_id = extract_item_id_from_create_response(create_response)

    with allure.step("Запросить статистику по объявлению"):
        statistics_response = api_client.get_statistics(created_item_id)

    with allure.step("Проверить структуру и значения статистики"):
        assert statistics_response.status_code == 200, statistics_response.text
        statistics = statistics_response.json()
        assert_statistics_shape(statistics)
        assert payload["statistics"] in statistics


@allure.epic("Avito internship API")
@allure.feature("POST /api/1/item")
@allure.story("Идемпотентность создания")
@allure.title("Повторное создание одинакового payload формирует новые сущности")
@allure.description("Проверка, что два одинаковых POST-запроса создают разные объявления с разными id.")
@pytest.mark.e2e
def test_creating_same_payload_twice_produces_different_ids(api_client, item_payload_factory):
    payload = item_payload_factory()

    with allure.step("Дважды отправить одинаковый payload"):
        first_response = api_client.create_item(payload)
        second_response = api_client.create_item(payload)

    with allure.step("Проверить, что оба объявления созданы и имеют разные id"):
        assert first_response.status_code == 200, first_response.text
        assert second_response.status_code == 200, second_response.text
        first_id = extract_item_id_from_create_response(first_response)
        second_id = extract_item_id_from_create_response(second_response)
        assert first_id != second_id

    with allure.step("Проверить, что оба объявления реально существуют и принадлежат одному продавцу"):
        first_get_response = api_client.get_item(first_id)
        second_get_response = api_client.get_item(second_id)
        assert first_get_response.status_code == 200, first_get_response.text
        assert second_get_response.status_code == 200, second_get_response.text
        first_item = first_get_response.json()[0]
        second_item = second_get_response.json()[0]
        assert_item_shape(first_item)
        assert_item_shape(second_item)
        assert first_item["sellerId"] == second_item["sellerId"] == payload["sellerID"]


@allure.epic("Avito internship API")
@allure.feature("POST /api/1/item")
@allure.story("Обязательные поля")
@allure.title("Создание объявления без обязательного поля возвращает 400")
@allure.description("Параметризованная проверка отсутствия обязательных полей в теле запроса.")
@pytest.mark.negative
@pytest.mark.parametrize("field_name", ["sellerID", "name", "price", "statistics"])
def test_create_item_without_required_field_returns_400(api_client, item_payload_factory, field_name):
    payload = item_payload_factory()
    payload.pop(field_name)

    with allure.step("Отправить запрос без обязательного поля {0}".format(field_name)):
        response = api_client.create_item(payload)

    with allure.step("Проверить ошибку валидации"):
        assert response.status_code == 400, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("POST /api/1/item")
@allure.story("Типы данных в payload")
@allure.title("Создание объявления с неверными типами данных возвращает 400")
@allure.description("Параметризованная проверка базовой валидации типов входных полей.")
@pytest.mark.negative
@pytest.mark.parametrize(
    ("overrides", "case_name"),
    [
        ({"sellerID": "not-an-int"}, "sellerID is string"),
        ({"name": 12345}, "name is integer"),
        ({"price": "100"}, "price is string"),
        ({"statistics": "wrong-type"}, "statistics is string"),
    ],
)
def test_create_item_with_invalid_types_returns_400(
    api_client, item_payload_factory, overrides, case_name
):
    payload = item_payload_factory(**overrides)

    with allure.step("Отправить некорректный payload: {0}".format(case_name)):
        response = api_client.create_item(payload)

    with allure.step("Проверить ошибку валидации"):
        assert response.status_code == 400, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/item/{id}")
@allure.story("Получение несуществующего объявления")
@allure.title("Запрос несуществующего объявления возвращает 404")
@allure.description("Проверка чтения объявления по валидному, но отсутствующему UUID.")
@pytest.mark.negative
def test_get_unknown_item_returns_404(api_client):
    with allure.step("Запросить заведомо несуществующий id объявления"):
        response = api_client.get_item(make_unknown_uuid())

    with allure.step("Проверить корректный ответ 404"):
        assert response.status_code == 404, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/statistic/{id}")
@allure.story("Получение статистики для несуществующего объявления")
@allure.title("Запрос статистики по несуществующему объявлению возвращает 404")
@allure.description("Проверка статистики по валидному, но отсутствующему UUID.")
@pytest.mark.negative
def test_get_statistics_for_unknown_item_returns_404(api_client):
    with allure.step("Запросить статистику по несуществующему id"):
        response = api_client.get_statistics(make_unknown_uuid())

    with allure.step("Проверить корректный ответ 404"):
        assert response.status_code == 404, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/{sellerID}/item")
@allure.story("Невалидный sellerID в path")
@allure.title("Запрос списка объявлений с невалидным sellerID возвращает 400")
@allure.description("Проверка валидации path-параметра sellerID.")
@pytest.mark.negative
def test_get_items_by_invalid_seller_id_returns_400(api_client):
    with allure.step("Запросить объявления с невалидным sellerID"):
        response = api_client.get_seller_items("invalid-seller-id")

    with allure.step("Проверить ошибку валидации"):
        assert response.status_code == 400, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("GET /api/1/item/{id}")
@allure.story("Время ответа ручки получения объявления")
@allure.title("Время ответа GET /item/{id} укладывается в заданный порог")
@allure.description("Легкая нефункциональная проверка времени ответа на чтение объявления.")
@pytest.mark.nonfunctional
def test_get_item_response_time_is_within_limit(api_client, item_payload_factory, max_response_time):
    payload = item_payload_factory()
    create_response = api_client.create_item(payload)
    assert create_response.status_code == 200, create_response.text
    created_item_id = extract_item_id_from_create_response(create_response)

    with allure.step("Получить объявление и измерить время ответа"):
        response = api_client.get_item(created_item_id)

    with allure.step("Проверить, что время ответа укладывается в порог"):
        assert response.status_code == 200, response.text
        assert response.elapsed_seconds <= max_response_time, (
            "Response time {0:.3f}s exceeded limit {1:.3f}s".format(
                response.elapsed_seconds, max_response_time
            )
        )


@allure.epic("Avito internship API")
@allure.feature("DELETE /api/2/item/{id}")
@allure.story("Удаление объявления по id")
@allure.title("Удаление существующего объявления по id")
@allure.description("E2E-проверка: объявление создается, удаляется и затем становится недоступным.")
@pytest.mark.e2e
def test_delete_item_v2_removes_created_item(api_client, item_payload_factory):
    payload = item_payload_factory()

    with allure.step("Создать объявление для последующего удаления"):
        create_response = api_client.create_item(payload)
        assert create_response.status_code == 200, create_response.text
        created_item_id = extract_item_id_from_create_response(create_response)

    with allure.step("Удалить объявление через v2"):
        delete_response = api_client.delete_item_v2(created_item_id)

    with allure.step("Проверить, что удаление завершилось успешно"):
        assert delete_response.status_code == 200, delete_response.text

    with allure.step("Проверить, что объявление больше недоступно"):
        get_response = api_client.get_item(created_item_id)
        assert get_response.status_code == 404, get_response.text


@allure.epic("Avito internship API")
@allure.feature("DELETE /api/2/item/{id}")
@allure.story("Удаление с невалидным id")
@allure.title("Удаление объявления с невалидным id возвращает 400")
@allure.description("Проверка валидации идентификатора в DELETE-ручке.")
@pytest.mark.negative
def test_delete_item_v2_with_invalid_id_returns_400(api_client):
    with allure.step("Удалить объявление с невалидным идентификатором"):
        response = api_client.delete_item_v2("invalid-item-id")

    with allure.step("Проверить ошибку валидации"):
        assert response.status_code == 400, response.text
        assert_error_response(response)


@allure.epic("Avito internship API")
@allure.feature("DELETE /api/2/item/{id}")
@allure.story("Удаление несуществующего объявления")
@allure.title("Удаление несуществующего объявления возвращает 404")
@allure.description("Проверка удаления по валидному, но отсутствующему UUID.")
@pytest.mark.negative
def test_delete_item_v2_with_unknown_id_returns_404(api_client):
    with allure.step("Удалить несуществующее объявление по валидному UUID"):
        response = api_client.delete_item_v2(make_unknown_uuid())

    with allure.step("Проверить ответ для отсутствующей сущности"):
        assert response.status_code == 404, response.text
        assert_error_response(response)
