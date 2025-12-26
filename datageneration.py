import random
import csv
from datetime import datetime


def generate_balanced_scenario():
    """Dengeli bir senaryo oluşturur"""
    # Standart süre: 16-24 hafta arası veya fixed 26 hafta(6 Ay)
    # Bedelli Askerlik Ücreti: 280 bin 850 lira 64 kuruş - 2025 2. yarısı
   # standard_duration = random.choice([16, 18, 20, 22, 24])
    standard_duration = 26

    # Paid1'in daha kısa mı daha uzun mı olacağını rastgele belirle
    paid1_shorter = random.choice([True, False])

    if paid1_shorter:
        # Paid1: standartın %10-30'u
        paid1_duration = max(0, int(standard_duration * random.uniform(0.1, 0.3)))
        # Paid2: Paid1'den uzun ama standarttan kısa
        paid2_duration = min(
            standard_duration - 1,
            max(paid1_duration + 1, int(standard_duration * random.uniform(0.3, 0.6)))
        )

        # Fiyatlar: Paid1 daha kısa → daha pahalı
        base_price = 280000
        paid1_price = int(base_price * (standard_duration - paid1_duration)*100 )
        paid2_price = int(paid1_price * random.uniform(0.5, 0.7))  # Paid2 daha ucuz

    else:
        # Paid1 daha uzun, Paid2 daha kısa
        # Paid1: standartın %30-60'ı
        paid1_duration = max(2, int(standard_duration * random.uniform(0.3, 0.6)))
        # Paid2: Paid1'den kısa
        paid2_duration = max(0, int(standard_duration * random.uniform(0.1, 0.3)))
        paid2_duration = min(paid2_duration, paid1_duration - 1)

        # Fiyatlar: Paid1 daha uzun → daha ucuz
        base_price = 280000
        paid1_price = int(base_price * (standard_duration - paid1_duration)*100 )
        paid2_price = int(paid1_price * random.uniform(1.3, 1.7))  # Paid2 daha pahalı

    # Fiyatları 10,000'lik katlara yuvarla (son 2 hane 00 olacak)
    paid1_price = round(paid1_price / 10000) * 10000
    paid2_price = round(paid2_price / 10000) * 10000

    # Minimum fiyat
    paid1_price = max(200000, paid1_price)
    paid2_price = max(200000, paid2_price)

    # Süreleri tam sayıya çevir
    paid1_duration = int(paid1_duration)
    paid2_duration = int(paid2_duration)

    return {
        'standard_duration': standard_duration,
        'paid1_duration': paid1_duration,
        'paid1_price': paid1_price,
        'paid2_duration': paid2_duration,
        'paid2_price': paid2_price
    }


def validate_scenario(scenario):
    """Senaryonun kurallara uygunluğunu kontrol et"""
    errors = []

    # Kurallar:
    # 1. Paid1 ve Paid2 süreleri standarttan küçük olmalı
    if scenario['paid1_duration'] >= scenario['standard_duration']:
        errors.append(
            f"Paid1 süresi ({scenario['paid1_duration']}) standarttan ({scenario['standard_duration']}) küçük olmalı")

    if scenario['paid2_duration'] >= scenario['standard_duration']:
        errors.append(
            f"Paid2 süresi ({scenario['paid2_duration']}) standarttan ({scenario['standard_duration']}) küçük olmalı")

    # 2. Trade-off kuralı:
    #    a) Paid1 > Paid2 ise Paid1 fiyatı < Paid2 fiyatı olmalı
    #    b) Paid1 < Paid2 ise Paid1 fiyatı > Paid2 fiyatı olmalı
    if scenario['paid1_duration'] > scenario['paid2_duration']:
        if scenario['paid1_price'] >= scenario['paid2_price']:
            errors.append(
                f"Paid1 daha uzun ({scenario['paid1_duration']} > {scenario['paid2_duration']}) ama daha ucuz değil ({scenario['paid1_price']} >= {scenario['paid2_price']})")
    elif scenario['paid1_duration'] < scenario['paid2_duration']:
        if scenario['paid1_price'] <= scenario['paid2_price']:
            errors.append(
                f"Paid1 daha kısa ({scenario['paid1_duration']} < {scenario['paid2_duration']}) ama daha pahalı değil ({scenario['paid1_price']} <= {scenario['paid2_price']})")
    else:
        # Süreler eşitse fiyatlar da eşit olmalı (bu durum nadir olmalı)
        if scenario['paid1_price'] != scenario['paid2_price']:
            errors.append(f"Süreler eşit ama fiyatlar farklı ({scenario['paid1_price']} != {scenario['paid2_price']})")

    # 3. Fiyatların son 2 hanesinin 00 olup olmadığını kontrol et
    if scenario['paid1_price'] % 1000 != 0:
        errors.append(f"Paid1 fiyatı son 3 hanesi 00 değil: {scenario['paid1_price']}")

    if scenario['paid2_price'] % 1000 != 0:
        errors.append(f"Paid2 fiyatı son 3 hanesi 00 değil: {scenario['paid2_price']}")

    return errors


def generate_scenarios(num_scenarios=10):
    """Belirtilen sayıda senaryo üret"""
    scenarios = []
    attempts = 0
    max_attempts_per_scenario = 100

    while len(scenarios) < num_scenarios:
        attempts += 1

        # Senaryo oluştur
        scenario = generate_balanced_scenario()

        # Doğrula
        errors = validate_scenario(scenario)

        # Geçerliyse listeye ekle
        if not errors:
            scenario['scenario_id'] = len(scenarios) + 1
            scenarios.append(scenario)
            attempts = 0  # Reset attempts for next scenario

        # Çok fazla deneme olursa uyarı ver
        if attempts >= max_attempts_per_scenario:
            print(f"Uyarı: Senaryo {len(scenarios) + 1} için {attempts} deneme yapıldı, basit senaryo kullanılıyor")
            # Basit geçerli senaryo (son 2 hanesi 00 olacak)
            scenario = {
                'scenario_id': len(scenarios) + 1,
                'standard_duration': 20,
                'paid1_duration': 4,
                'paid1_price': 400000,
                'paid2_duration': 2,
                'paid2_price': 600000
            }
            scenarios.append(scenario)
            attempts = 0

    return scenarios


def save_to_csv(scenarios, filename='scenarios.csv'):

    fieldnames = [
        'scenario_id',
        'standard_duration',
        'standard_price',
        'paid1_duration',
        'paid1_price',
        'paid2_duration',
        'paid2_price',
        'tradeoff_type',
        'duration_ratio',
        'price_ratio'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for scenario in scenarios:
            # Ekstra bilgiler hesapla
            if scenario['paid1_duration'] > scenario['paid2_duration']:
                tradeoff_type = 'Paid1_daha_uzun_ucuz'
            else:
                tradeoff_type = 'Paid1_daha_kısa_pahalı'

            duration_ratio = scenario['paid1_duration'] / scenario['paid2_duration'] if scenario[
                                                                                            'paid2_duration'] > 0 else float(
                'inf')
            price_ratio = scenario['paid1_price'] / scenario['paid2_price']

            row = {
                'scenario_id': scenario['scenario_id'],
                'standard_duration': scenario['standard_duration'],
                'standard_price': 0,
                'paid1_duration': scenario['paid1_duration'],
                'paid1_price': scenario['paid1_price'],
                'paid2_duration': scenario['paid2_duration'],
                'paid2_price': scenario['paid2_price'],
                'tradeoff_type': tradeoff_type,
                'duration_ratio': round(duration_ratio, 2),
                'price_ratio': round(price_ratio, 2)
            }

            writer.writerow(row)

    print(f"{len(scenarios)} senaryo '{filename}' dosyasına kaydedildi.")


def print_summary(scenarios):
    print("\n" + "=" * 60)
    print("ÖZET ")
    print("=" * 60)

    print(f"\nToplam Senaryo Sayısı: {len(scenarios)}")

    # İstatistikler
    standard_durations = [s['standard_duration'] for s in scenarios]
    paid1_durations = [s['paid1_duration'] for s in scenarios]
    paid2_durations = [s['paid2_duration'] for s in scenarios]
    paid1_prices = [s['paid1_price'] for s in scenarios]
    paid2_prices = [s['paid2_price'] for s in scenarios]

    print(f"\nStandart Süre Dağılımı:")
    for duration in sorted(set(standard_durations)):
        count = standard_durations.count(duration)
        print(f"  {duration} hafta: {count} senaryo ({count / len(scenarios) * 100:.1f}%)")

    print(f"\nPaid1 Süre Ortalaması: {sum(paid1_durations) / len(paid1_durations):.1f} hafta")
    print(f"Paid2 Süre Ortalaması: {sum(paid2_durations) / len(paid2_durations):.1f} hafta")

    print(f"\nPaid1 Fiyat Ortalaması: {sum(paid1_prices) / len(paid1_prices):,.0f} TL")
    print(f"Paid2 Fiyat Ortalaması: {sum(paid2_prices) / len(paid2_prices):,.0f} TL")

    # Fiyat son 2 hane kontrolü
    paid1_valid = sum(1 for p in paid1_prices if p % 1000 == 0)
    paid2_valid = sum(1 for p in paid2_prices if p % 1000 == 0)

    print(f"\nFiyat Formatı Kontrolü:")
    print(
        f"  Paid1 fiyatları son 2 hanesi 00: {paid1_valid}/{len(scenarios)} ({paid1_valid / len(scenarios) * 100:.1f}%)")
    print(
        f"  Paid2 fiyatları son 2 hanesi 00: {paid2_valid}/{len(scenarios)} ({paid2_valid / len(scenarios) * 100:.1f}%)")

    # Trade-off türleri
    paid1_shorter_count = sum(1 for s in scenarios if s['paid1_duration'] < s['paid2_duration'])
    paid1_longer_count = sum(1 for s in scenarios if s['paid1_duration'] > s['paid2_duration'])
    equal_count = sum(1 for s in scenarios if s['paid1_duration'] == s['paid2_duration'])

    print(f"\nTrade-off Dağılımı:")
    print(
        f"  Paid1 daha kısa ve daha pahalı: {paid1_shorter_count} senaryo ({paid1_shorter_count / len(scenarios) * 100:.1f}%)")
    print(
        f"  Paid1 daha uzun ve daha ucuz: {paid1_longer_count} senaryo ({paid1_longer_count / len(scenarios) * 100:.1f}%)")
    if equal_count > 0:
        print(f"  Süreler eşit: {equal_count} senaryo ({equal_count / len(scenarios) * 100:.1f}%)")

    # İlk 5 senaryoyu göster
    print(f"\nİlk 5 Senaryo:")
    print("-" * 80)
    print(f"{'ID':<4} {'Standart':<10} {'Paid1':<15} {'Paid2':<15} {'Trade-off':<20}")
    print("-" * 80)

    for i, scenario in enumerate(scenarios[:5]):
        standard = f"{scenario['standard_duration']} hafta"
        paid1 = f"{scenario['paid1_duration']} hafta, {scenario['paid1_price']:,} TL"
        paid2 = f"{scenario['paid2_duration']} hafta, {scenario['paid2_price']:,} TL"

        if scenario['paid1_duration'] < scenario['paid2_duration']:
            tradeoff = "Paid1 kısa/pahalı"
        else:
            tradeoff = "Paid1 uzun/ucuz"

        print(f"{scenario['scenario_id']:<4} {standard:<10} {paid1:<15} {paid2:<15} {tradeoff:<20}")

    print("-" * 80)


def print_simple_table(scenarios, num_to_show=10):
    print(f"\n{'ID':<4} {'Standart':<10} {'Paid1':<25} {'Paid2':<25}")
    print("-" * 70)

    for i, scenario in enumerate(scenarios[:num_to_show]):
        standard = f"{scenario['standard_duration']} hafta"
        paid1 = f"{scenario['paid1_duration']} hafta, {scenario['paid1_price']:,} TL"
        paid2 = f"{scenario['paid2_duration']} hafta, {scenario['paid2_price']:,} TL"
        print(f"{scenario['scenario_id']:<4} {standard:<10} {paid1:<25} {paid2:<25}")


def create_qualtrics_import_csv(scenarios, filename='qualtrics_import.csv'):
    """Qualtrics'e import için uygun CSV oluştur"""
    # Her senaryo için farklı değişkenler
    fieldnames = ['scenario_id']

    # Her senaryo için değişken adları oluştur
    for i in range(1, len(scenarios) + 1):
        fieldnames.extend([
            f'standard_duration_{i}',
            f'paid1_duration_{i}',
            f'paid1_price_{i}',
            f'paid2_duration_{i}',
            f'paid2_price_{i}',
            f'tradeoff_type_{i}'
        ])

    # Sadece 1 satırlık veri (tüm senaryolar)
    row = {'scenario_id': 'all_scenarios'}

    for i, scenario in enumerate(scenarios, 1):
        row[f'standard_duration_{i}'] = scenario['standard_duration']
        row[f'paid1_duration_{i}'] = scenario['paid1_duration']
        row[f'paid1_price_{i}'] = scenario['paid1_price']
        row[f'paid2_duration_{i}'] = scenario['paid2_duration']
        row[f'paid2_price_{i}'] = scenario['paid2_price']

        if scenario['paid1_duration'] < scenario['paid2_duration']:
            row[f'tradeoff_type_{i}'] = 'Paid1_kısa_pahalı'
        else:
            row[f'tradeoff_type_{i}'] = 'Paid1_uzun_ucuz'

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    print(f"\nQualtrics import dosyası '{filename}' oluşturuldu.")


def main():
    print("Başlatılıyor...")

    # Senaryoları oluştur
    print("\n100 senaryo oluşturuluyor...")
    scenarios = generate_scenarios(100)

    # Özet yazdır
    print_summary(scenarios)

    # Basit tablo göster
    print_simple_table(scenarios, 10)

    # CSV'ye kaydet
    save_to_csv(scenarios, 'scenarios.csv')

    # Qualtrics için CSV oluştur
    create_qualtrics_import_csv(scenarios, 'qualtrics_scenarios.csv')

    # Ek olarak JSON formatında da kaydet
    import json
    with open('scenarios.json', 'w', encoding='utf-8') as f:
        json.dump(scenarios, f, indent=2, ensure_ascii=False)
    print(f"\nJSON formatında 'scenarios.json' dosyasına kaydedildi.")

    print("\n" + "=" * 60)
    print("İŞLEM TAMAMLANDI!")
    print("=" * 60)
    print("\nOluşturulan dosyalar:")
    print("1. scenarios.csv - Tüm senaryolar")
    print("2. qualtrics_scenarios.csv - Qualtrics import için")
    print("3. scenarios.json - JSON formatında")


if __name__ == "__main__":
    main()