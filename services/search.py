import yadisk


TOKEN = "y0__xC9xu6BBhjc1jwgqL7o8RWGkcNghbCfof-5T4IJe74HTprUig"

client = yadisk.Client(token=TOKEN)

if client.check_token():
    print("Токен валиден")
else:
    print("Токен невалиден")
    exit()

disk_info = client.get_disk_info()
print(f"Всего места: {disk_info.total_space} байт")
print(f"Использовано: {disk_info.used_space} байт")

client.close()
