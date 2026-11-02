import sys

import config
from processor import AdBannerError, AdBannerGenerator

FORMAT_OPTIONS = {
    1: ("story", "Story/WhatsApp (9:16)"),
    2: ("feed", "Feed (4:5)"),
}

SERVICES = {
    1: ("Aire Acondicionado", "¿EL AIRE NO ENFRÍA?", "PRECISION A/C SERVICE"),
    2: ("Frenos y Suspensión", "¿RUIDO AL FRENAR?", "BRAKE SYSTEM EXPERTS"),
    3: ("Diagnóstico Check Engine", "¿FALLAS EN EL MOTOR?", "COMPUTER DIAGNOSTICS"),
    4: ("Mantenimiento General", "MANTENIMIENTO PREVENTIVO", "EXPERT AUTO SERVICE"),
}
CUSTOM_OPTION = 5


def list_photos():
    if not config.INPUT_DIR.is_dir():
        return []
    return sorted(
        p for p in config.INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in config.VALID_EXTENSIONS
    )


def ask_int(prompt, valid):
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and int(raw) in valid:
            return int(raw)
        print(f"  ✗ Opción inválida. Ingresa un número entre {min(valid)} y {max(valid)}.")


def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  ✗ Este campo no puede estar vacío.")


def main():
    print(f"=== {config.BUSINESS_NAME} · Generador de anuncios ===\n")

    photos = list_photos()
    if not photos:
        print(f"No hay imágenes en {config.INPUT_DIR}")
        print("Copia tus fotos (.jpg, .jpeg, .png, .webp) ahí y vuelve a ejecutar.")
        return 1

    print("Fotos disponibles:")
    for i, p in enumerate(photos, 1):
        print(f"  [{i}] {p.name}")
    photo = photos[ask_int("\nSelecciona el número de la foto: ", range(1, len(photos) + 1)) - 1]

    print("\nFormato de salida:")
    for k, (_, label) in FORMAT_OPTIONS.items():
        print(f"  [{k}] {label}")
    format_key = FORMAT_OPTIONS[ask_int("\nSelecciona el formato: ", FORMAT_OPTIONS)][0]

    print("\nServicio a promocionar:")
    for k, (name, headline, sub) in SERVICES.items():
        print(f"  [{k}] {name}  ({headline} / {sub})")
    print(f"  [{CUSTOM_OPTION}] Personalizado")
    choice = ask_int("\nSelecciona el servicio: ", range(1, CUSTOM_OPTION + 1))

    if choice == CUSTOM_OPTION:
        headline = ask_text("Titular (español): ")
        subtitle = ask_text("Subtítulo (inglés): ")
        service = ask_text("Nombre del servicio: ")
    else:
        service, headline, subtitle = SERVICES[choice]

    try:
        out = AdBannerGenerator(format_key).generate(photo, headline, subtitle, service)
    except AdBannerError as e:
        print(f"\n✗ Error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}")
        return 1

    print(f"\n✓ Anuncio generado con éxito:\n  {out.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nOperación cancelada.")
        sys.exit(130)
