from django.urls import path

from apps.gis.views import (
    map_page,
    destinations_page,
    village_geojson,
    village_points_geojson,
    destination_geojson,
    elevation_zones_geojson,
    characteristic_zones_geojson,
    legend,
    itinerary_page,
    itinerary_excel,
    # Management (staff/superuser)
    RegionCharacteristicListView,
    RegionCharacteristicCreateView,
    RegionCharacteristicUpdateView,
    RegionCharacteristicDeleteView,
    RegionElevationListView,
    RegionElevationCreateView,
    RegionElevationUpdateView,
    RegionElevationDeleteView,
    TourismCategoryListView,
    TourismCategoryCreateView,
    TourismCategoryUpdateView,
    TourismCategoryDeleteView,
    TouristDestinationListView,
    TouristDestinationCreateView,
    TouristDestinationUpdateView,
    TouristDestinationDeleteView,
    update_destination_price,
    update_destination_type,
)


urlpatterns = [
    path("", map_page, name="map"),

    path(
        "destinations/",
        destinations_page,
        name="destinations",
    ),

    path(
        "itinerary/",
        itinerary_page,
        name="itinerary",
    ),

    path(
        "itinerary/excel/",
        itinerary_excel,
        name="itinerary-excel",
    ),

    # ---------------- API (JSON) ----------------
    path(
        "api/villages/geojson/",
        village_geojson,
        name="api-villages-geojson",
    ),
    path(
        "api/villages/points/geojson/",
        village_points_geojson,
        name="api-villages-points-geojson",
    ),
    path(
        "api/destinations/geojson/",
        destination_geojson,
        name="api-destinations-geojson",
    ),
    path(
        "api/elevation-zones/geojson/",
        elevation_zones_geojson,
        name="api-elevation-zones-geojson",
    ),
    path(
        "api/characteristic-zones/geojson/",
        characteristic_zones_geojson,
        name="api-characteristic-zones-geojson",
    ),
    path(
        "api/legend/",
        legend,
        name="api-legend",
    ),

    # ---------------- Management (Kelola Data) ----------------
    path(
        "manage/region-characteristics/",
        RegionCharacteristicListView.as_view(),
        name="manage-characteristic-list",
    ),
    path(
        "manage/region-characteristics/create/",
        RegionCharacteristicCreateView.as_view(),
        name="manage-characteristic-create",
    ),
    path(
        "manage/region-characteristics/<int:pk>/update/",
        RegionCharacteristicUpdateView.as_view(),
        name="manage-characteristic-update",
    ),
    path(
        "manage/region-characteristics/<int:pk>/delete/",
        RegionCharacteristicDeleteView.as_view(),
        name="manage-characteristic-delete",
    ),

    path(
        "manage/elevations/",
        RegionElevationListView.as_view(),
        name="manage-elevation-list",
    ),
    path(
        "manage/elevations/create/",
        RegionElevationCreateView.as_view(),
        name="manage-elevation-create",
    ),
    path(
        "manage/elevations/<int:pk>/update/",
        RegionElevationUpdateView.as_view(),
        name="manage-elevation-update",
    ),
    path(
        "manage/elevations/<int:pk>/delete/",
        RegionElevationDeleteView.as_view(),
        name="manage-elevation-delete",
    ),

    path(
        "manage/tourism-categories/",
        TourismCategoryListView.as_view(),
        name="manage-category-list",
    ),
    path(
        "manage/tourism-categories/create/",
        TourismCategoryCreateView.as_view(),
        name="manage-category-create",
    ),
    path(
        "manage/tourism-categories/<int:pk>/update/",
        TourismCategoryUpdateView.as_view(),
        name="manage-category-update",
    ),
    path(
        "manage/tourism-categories/<int:pk>/delete/",
        TourismCategoryDeleteView.as_view(),
        name="manage-category-delete",
    ),

    path(
        "manage/destinations/",
        TouristDestinationListView.as_view(),
        name="manage-destination-list",
    ),
    path(
        "manage/destinations/create/",
        TouristDestinationCreateView.as_view(),
        name="manage-destination-create",
    ),
    path(
        "manage/destinations/<int:pk>/update/",
        TouristDestinationUpdateView.as_view(),
        name="manage-destination-update",
    ),
    path(
        "manage/destinations/<int:pk>/delete/",
        TouristDestinationDeleteView.as_view(),
        name="manage-destination-delete",
    ),
    path(
        "manage/destinations/<int:pk>/update-price/",
        update_destination_price,
        name="manage-destination-update-price",
    ),
    path(
        "manage/destinations/<int:pk>/move/",
        update_destination_type,
        name="manage-destination-move",
    ),
]
