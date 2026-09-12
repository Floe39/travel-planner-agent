"""旅行数据工具层。

当前实现故意使用本地 Mock 数据，使项目可离线演示。生产环境只需实现同名
TravelDataProvider，即可替换为航旅/酒店供应商，不影响图编排和业务校验。
"""
from .schemas import Activity, Flight, Hotel, TripRequest


class MockTravelDataProvider:
    def search_flights(self, request: TripRequest) -> list[Flight]:
        return [
            Flight(id="flight-comfort", airline="星途航空", departure="08:10", arrival="12:05", price_per_person=1280, duration_hours=3.9),
            Flight(id="flight-value", airline="云航", departure="13:40", arrival="17:50", price_per_person=920, duration_hours=4.2),
            Flight(id="flight-budget", airline="远行航空", departure="21:20", arrival="02:10", price_per_person=680, duration_hours=4.8),
        ]

    def search_hotels(self, request: TripRequest) -> list[Hotel]:
        return [
            Hotel(id="hotel-comfort", name=f"{request.destination}城市景观酒店", rating=4.8, price_per_night=820, amenities=["早餐", "健身房", "接送服务"]),
            Hotel(id="hotel-value", name=f"{request.destination}中心酒店", rating=4.4, price_per_night=480, amenities=["早餐", "地铁近"]),
            Hotel(id="hotel-budget", name=f"{request.destination}轻居酒店", rating=4.1, price_per_night=280, amenities=["WIFI", "自助洗衣"]),
        ]

    def search_activities(self, request: TripRequest) -> list[Activity]:
        return [
            Activity(id="city-tour", name="城市文化漫步", duration_hours=4, price_per_person=180),
            Activity(id="museum", name="博物馆与展览", duration_hours=3, price_per_person=120),
            Activity(id="food-tour", name="本地美食体验", duration_hours=3, price_per_person=260),
            Activity(id="night-view", name="夜景观光", duration_hours=2, price_per_person=160),
        ]
