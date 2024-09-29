from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

# Подключение маршрутов для i18n
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('segmentation.urls')),
    path('', include('data_preparation.urls')),  # Добавляем ваше приложение
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
