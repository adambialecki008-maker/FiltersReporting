from filters_reporting.database.filters_repository import FiltersRepository
from filters_reporting.config import *
from filters_reporting.collection.simulator import generate_current_samples
from filters_reporting.collection.data_collector import run_collector
from datetime import date
from filters_reporting.models.filter import Filter
from filters_reporting.reporting.excel_report import create_excel_report
from filters_reporting.reporting.text_report import (
    build_filter_statistics_report,
    save_report_to_txt,
)
import asyncio
from filters_reporting.reporting.email_reporting import *
from filters_reporting.reporting.report_service import (
    generate_reports_for_day,
    generate_and_send_reports_for_day as send_reports_for_day,
)

email_config = EmailConfig(
    smtp_host=SMTP_HOST,
    smtp_port=SMTP_PORT,
    username=EMAIL_USERNAME,
    sender=EMAIL_SENDER,
    recipients=EMAIL_RECIPIENTS,
)


def show_menu():
    print("------Menu wyboru-----")
    print("-" * 30)
    print("1. Dodaj nowy filtr")
    print("2. Pokaż filtry")
    print("3. Aktywuj/Dezaktywuj")
    print("4. Generuj dzisiejsze próbki")
    print("5. Pokaż próbki filtra")
    print("6. Pokaż statystyki delta_p")
    print("7. Pokaż statystyki danego dnia")
    print("8. Generuj próbki co minute")
    print("9. Usuń dzisiejsze próbki")
    print("10. Modyfikuj opc_url filtra")
    print("11. Wyczyść log collectora")
    print("12. Generuj i wyślij raport dzienny")
    print("X. Zakończ")
    print("=" * 30)
    choice = input("Wybierz opcję: ")
    return choice


def add_filter(repository):
    filter_name = input("Podaj nazwę filtra: ")
    if repository.get_filter_by_name(filter_name):
        print("Taka nazwa już istnieje")
        return
    opc_url = input("Podaj opc_url filtra")
    while repository.get_filter_by_opc_url(opc_url) is not None:
        print("Takie opc_url już istnieje, podaj inne")
        opc_url = input("Podaj opc_url filtra: ")
    new_filter = Filter(name=filter_name, opc_url=opc_url)
    repository.save_filter(new_filter)


def show_filters(repository):
    filters = repository.get_all_filters()
    print(f"Liczba filtrów w bazie: {len(filters)}")
    for filter_obj in filters:
        print("-" * 30)
        print(f"ID: {filter_obj.filter_id}")
        print(f"Nazwa: {filter_obj.name}")
        print(f"opc_url: {filter_obj.opc_url}")
        if filter_obj.active:
            print("Filtr aktywny")
        else:
            print("Filtr wyłączony")


def activate_deactivate_filter(repository):
    filter_name = input("Podaj nazwę filtra: ")
    if not repository.get_filter_by_name(filter_name):
        print("Brak takiego urządzenia w bazie")
        return
    activate = input("Aktywuj t/n :")
    if activate.lower() == "t":
        if_activate = True
    elif activate.lower() == "n":
        if_activate = False
    else:
        print("Błędny parametr")
        return
    repository.update_filter_activity(filter_name, if_activate)
    updated_filter = repository.get_filter_by_name(filter_name)
    print("-" * 30)
    print(f"ID: {updated_filter.filter_id}")
    print(f"Nazwa: {updated_filter.name}")
    if updated_filter.active:
        print("Filtr aktywny")
    else:
        print("Filtr wyłączony")


def update_filter_opc_url(repository):
    filter_name = input("Podaj nazwę filtra: ")
    if not repository.get_filter_by_name(filter_name):
        print("Brak takiego urządzenia w bazie")
        return
    opc_url = input("Podaj opc_url filtra: ")
    while repository.get_filter_by_opc_url(opc_url):
        print("Takie opc_url już istnieje")
        opc_url = input("Podaj opc_url filtra: ")
    repository.update_filter_opc_url(filter_name, opc_url)
    updated_filter = repository.get_filter_by_opc_url(opc_url)
    print("-" * 30)
    print(f"ID: {updated_filter.filter_id}")
    print(f"Nazwa: {updated_filter.name}")
    print(f"OPC_URL: {updated_filter.opc_url}")


def generate_samples(repository):
    filters = repository.get_active_filters()

    if not filters:
        print("Brak aktywnych filtrów")
        return
    samples = generate_current_samples(filters)
    for sample in samples:
        repository.save_filter_sample(sample)
    sample_count = len(samples)
    if sample_count != 0:
        print(f"Wygenerowano {sample_count} próbek")


def get_samples_by_name(repository):
    filter_name = input(f"Pokaż próbki dla filtra: ")
    filter_obj = repository.get_filter_by_name(filter_name)
    if not filter_obj:
        print(f"Brak filtra {filter_name} ")
        return
    chosen_day = get_date_from_user()
    if chosen_day is None:
        return
    samples_by_id = repository.get_filter_samples_by_filter_id(
        filter_obj.filter_id, chosen_day
    )
    if samples_by_id:
        for sample_by_id in samples_by_id:
            print(
                f"Nazwa: {sample_by_id[0]} | "
                f"Delta_P: {sample_by_id[1]} | "
                f"Czas: {sample_by_id[2]}"
            )
    else:
        print("Brak próbek dla tego dnia")


def delete_today_samples(repository):
    today = date.today().isoformat()
    deleted = repository.delete_samples_for_day(today)
    print(f"Usunięto {deleted} próbek z dnia {today}")


def show_filter_statistics(repository):
    filter_name = input(f"Podaj nazwę filtra: ")
    filter_obj = repository.get_filter_by_name(filter_name)
    if not filter_obj:
        print(f"Brak filtra o nazwie {filter_name}")
        return
    chosen_day = get_date_from_user()
    if chosen_day is None:
        return
    stats = repository.get_delta_p_stats_by_filter_id(filter_obj.filter_id, chosen_day)
    if stats is not None:
        minimum = stats[0]
        maximum = stats[1]
        average = stats[2]
        count = stats[3]
        alarms_active = stats[4]
        status = stats[5]
        print(f"Minimum: {minimum}")
        print(f"Maximum: {maximum}")
        print(f"Srednia: {average}")
        print(f"Liczba próbek: {count}")
        print(f"Liczba alarmów: {alarms_active}")
        if count != 0:
            print(f"Alarm był aktywny w {alarms_active / count * 100:.1f}% próbek")
        print(f"Liczba próbek podczas pracy filtra: {status}")
        if status != 0:
            print(f"Filtr pracował w {status / count * 100:.1f}% próbek")

    else:
        print("Brak")


def daily_filter_report(repository):
    chosen_day = get_date_from_user()
    if chosen_day is None:
        return
    generate_reports_for_day(repository, chosen_day)


def get_date_from_user():
    chosen_day = input("Podaj dzień YYYY-MM-DD: ")
    try:
        date.fromisoformat(chosen_day)
        return chosen_day
    except ValueError:
        print("Zły format daty")
        return None


def clean_log():
    try:
        with open("collector.log", "w", encoding="utf-8") as file:
            pass
    except Exception as e:
        print(f"Błąd usuwania collector.log: {e}")


def generate_and_send_reports_for_day(repository):
    chosen_day = get_date_from_user()

    if chosen_day is None:
        return

    result = send_reports_for_day(
        repository,
        chosen_day,
        email_config,
    )

    if result is None:
        print("Brak danych do raportu")
        return

    print(f"Wysłano raport dla {chosen_day}")


repository = FiltersRepository(DATABASE_NAME)
repository.create_table()
# repository.migrate_add_active()

# main loop##################################################################
if __name__ == "__main__":
    while True:
        choice = show_menu()
        if choice.lower() == "x":
            break
        elif choice == "1":
            add_filter(repository)
        elif choice == "2":
            show_filters(repository)
        elif choice == "3":
            activate_deactivate_filter(repository)
        elif choice == "4":
            generate_samples(repository)
        elif choice == "5":
            get_samples_by_name(repository)
        elif choice == "6":
            show_filter_statistics(repository)
        elif choice == "7":
            daily_filter_report(repository)
        elif choice == "8":
            asyncio.run(run_collector())
        elif choice == "9":
            delete_today_samples(repository)
        elif choice == "10":
            update_filter_opc_url(repository)
        elif choice == "11":
            clean_log()
        elif choice == "12":
            generate_and_send_reports_for_day(repository)
