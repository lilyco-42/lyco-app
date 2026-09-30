# Android 权限清单（侧载优先）

| 权限 | 用途 | AI 能力 |
|------|------|---------|
| ACCESS_FINE_LOCATION / COARSE_LOCATION | 定位 | 1km POI 搜索原点 |
| ACCESS_BACKGROUND_LOCATION | 后台定位 | 到店提醒、轨迹 |
| CAMERA | 拍照 | 拍店招/扫码/多模态问答 |
| RECORD_AUDIO | 录音 | 语音输入 |
| READ_CONTACTS | 通讯录 | 熟人推荐（敏感，按需申请） |
| POST_NOTIFICATIONS | 通知 | 优惠/排队提醒 |
| INTERNET / FOREGROUND_SERVICE / RECEIVE_BOOT_COMPLETED | 基础 | 常驻推理服务 |
| READ_MEDIA_IMAGES / READ_MEDIA_VIDEO | 相册 | 图库问答 |
| READ_CALENDAR | 日历 | 行程结合推荐 |

暂缓（上架高危，侧载可谈）：READ_SMS、READ_CALL_LOG、READ_PHONE_STATE。
iOS 侧：定位（WhenInUse/Always）、相机、麦克风、通知、通讯录逐项申请，
以后台定位和通讯录最难拿，需配使用说明文案。
