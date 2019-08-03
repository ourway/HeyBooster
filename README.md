# [BootsRoas](https://www.boostroas.com/) HeyBooster

**Proje Bilgileri**
* **Framework**: Flask==1.1.1

**Yapılacaklar**
* ~~Kanala Slack Bot Bağlama ve Veri Yollama~~
* Google hesabı bağlama
* Google analytics hesabı bağlama
* Bağlanan hesapların verilerini çekme

**Alınabilecek Hatalar**
```
oauthlib.oauth2.rfc6749.errors.InsecureTransportError

oauthlib.oauth2.rfc6749.errors.InsecureTransportError: (insecure_transport) OAuth 2 MUST utilize https.
```
Çözüm: export OAUTHLIB_INSECURE_TRANSPORT=1