# Replaces only the right-half nice!view screen. Upstream's widget is turned
# off there (CONFIG_NICE_VIEW_WIDGET_STATUS=n), so we reuse its helpers by path.
if(CONFIG_CORNE_NICE_VIEW_ART)
  set(nice_view_widgets ${APPLICATION_SOURCE_DIR}/boards/shields/nice_view/widgets)
  zephyr_library()
  zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include ${nice_view_widgets})
  zephyr_library_sources(
    ${nice_view_widgets}/util.c
    ${nice_view_widgets}/bolt.c
    peripheral_status.c
    art.c
  )
endif()
