"""Build a portable, editable feature tour using the application's own model."""
from dataclasses import replace
import io
from pathlib import Path
import sys
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from presentationpresenter.domain import (
    Presentation, TextSection, TextBlock, TextRun, TextStyle, BlockKind,
    ImageSection, ImageItem, ImagePlacement, OutputConfig, Aspect, CameraRegion,
)
from presentationpresenter.bible import BibleService
from presentationpresenter.media import from_bytes
from presentationpresenter.storage import save, load
from presentationpresenter.layout import paginate
from presentationpresenter.rendering import TkMetrics, draw
from presentationpresenter.layout import Typography


def block(text, kind=BlockKind.PARAGRAPH, level=0, **style):
    return TextBlock((TextRun(text, TextStyle(family='Calibri', **style)),), kind, level=level)


def build():
    media = []
    for color, size in (('#ef6351', (640, 360)), ('#35a7a0', (360, 540)),
                        ('#f4bf4f', (480, 480)), ('#9275d3', (800, 300))):
        buffer = io.BytesIO()
        Image.new('RGB', size, color).save(buffer, format='PNG')
        media.append(from_bytes(buffer.getvalue()))
    sections = []

    def text(title, *blocks, **kwargs):
        section = TextSection(title, tuple(blocks), **kwargs)
        sections.append(section)
        return section

    text('01 • Vítejte', block('PresentationPresenter', size=52, bold=True),
         block('Vzorová prezentace všech hlavních možností aplikace.'),
         block('Sál 4:3 • stream 16:9 • kamera vpravo dole', color='#f4bf4f'),
         block('Barevné obdélníky zastupují obrázky. Doprovodný návod obsahuje další pokusy.'))
    text('02 • Název, odkaz a odstavce',
         block('Toto je první odstavec. Text můžete upravovat přímo v editoru.'),
         block('Druhý odstavec zůstává samostatný. Název úseku a odkaz jsou oddělená pole.'),
         reference='Ukázka odkazu • Jan 3:16–18')
    text('03 • Formátování uvnitř textu',
         TextBlock((TextRun('Běžný text, ', TextStyle(family='Calibri')),
                    TextRun('tučný důraz', TextStyle(family='Calibri', bold=True)),
                    TextRun(', kurzíva', TextStyle(family='Calibri', italic=True)),
                    TextRun(' a podtržení.', TextStyle(family='Calibri', underline=True)))),
         block('Barevný text', color='#f4bf4f'),
         block('Menší písmo • 28', size=28), block('Větší písmo • 48', size=48),
         block('Jiný font: Georgia', size=32))
    sections[-1] = replace(sections[-1], blocks=sections[-1].blocks[:-1] + (
        TextBlock((TextRun('Jiný font: Georgia', TextStyle(family='Georgia', size=32)),)),))
    text('04 • Odrážky a úrovně',
         block('První hlavní bod', BlockKind.BULLET),
         block('Podrobnost první úrovně', BlockKind.BULLET, 1),
         block('Ještě podrobnější bod', BlockKind.BULLET, 2),
         block('Druhý hlavní bod', BlockKind.BULLET),
         block('Odstavec mimo seznam.'))
    text('05 • Číslovaný seznam',
         block('Připravte obsah.', BlockKind.NUMBERED),
         block('Zkontrolujte oba náhledy.', BlockKind.NUMBERED),
         block('Podrobnost kroku', BlockKind.NUMBERED, 1),
         block('Potvrďte změny do projekce.', BlockKind.NUMBERED))
    story = ('Na cestu jsme vyrazili brzy ráno. Za vesnicí se otevřel výhled do údolí. '
             'Zastavili jsme se, abychom si společně přečetli další část příběhu. '
             'Každý mohl přidat otázku a pak jsme pokračovali dál. ')
    text('06 • Automatické dělení dlouhého textu',
         block(story * 7), block('Druhý odstavec příběhu. ' + story * 5),
         reference='Společný obsah • různé zalomení sálu a streamu')
    text('07 • Dlouhá odrážka a pokračování',
         block('Tato odrážka pokračuje přes více snímků. ' + story * 7, BlockKind.BULLET),
         block('Další bod začíná až po dokončení předchozího.', BlockKind.BULLET))
    passage = BibleService().parse('CSP', 'Jan 3:16–18')
    for title, numbers, separate in (('08 • Bible souvisle bez čísel', False, False),
                                     ('09 • Bible souvisle s čísly', True, False),
                                     ('10 • Bible po verších s čísly', True, True)):
        sections.append(replace(passage.section(numbers, separate), title=title))
    text('11 • Čtení bez černého předělu A', block('Tato pasáž přejde rovnou na další úsek.'),
         reference='Ukázková pasáž A', break_after=False)
    text('12 • Čtení bez černého předělu B', block('Mezi těmito dvěma úseky není černý snímek.'),
         reference='Ukázková pasáž B', break_before=False)
    text('13 • Sloučení — první část', block('První část byla původně na jednom snímku.'),
         reference='Přísloví 2:16 • ukázka sloučení', break_after=False)
    text('14 • Sloučení — druhá část', block('Druhá část byla na dalším. Zkuste oba úseky sloučit a nechat text znovu rozdělit aplikací.'),
         reference='Přísloví 2:16 • ukázka sloučení')
    sections.append(ImageSection('15 • Samostatný obrázek', media[0].id,
                                 alt_text='Korálový obdélník na šířku'))
    text('16 • Automatická mřížka obrázků',
         images=tuple(ImageItem(asset.id, alt_text=f'Barevný obdélník {i+1}')
                      for i, asset in enumerate(media)))
    text('17 • Text a obrázek společně',
         block('Text obtéká barevný obdélník. Ve streamu navíc respektuje prostor kamery.'),
         block(story * 3), images=(ImageItem(media[1].id, alt_text='Tyrkysový svislý obdélník'),))
    text('18 • Ruční umístění pro každý výstup',
         block('Obdélníky mají v sále jiné pozice než ve streamu. Výstupy jsou pro tento úsek odpojené.'),
         block('Táhněte obrázek nebo jeho roh. Escape zruší tah. Při vypnutých přímých úpravách nejprve použijte Domů → Upravit obrázky.', size=28),
         block('Nastavení → Úprava obrázků napřímo: výchozí stav je zapnuto.', size=28),
         images=(ImageItem(media[0].id, hall=ImagePlacement(.06, .45, .34),
                           stream=ImagePlacement(.04, .38, .26)),
                 ImageItem(media[2].id, hall=ImagePlacement(.61, .48, .23),
                           stream=ImagePlacement(.34, .43, .18))), stream_linked=False)
    text('19 • Obrázek jen na prvním pokračování',
         block('Žlutý obdélník se objeví pouze na prvním pokračování tohoto úseku. ' + story * 8),
         images=(ImageItem(media[2].id, repeat=False, alt_text='Žlutý čtverec pouze na začátku'),))
    text('20 • Obrázek na všech pokračováních',
         block('Fialový obdélník se opakuje na všech pokračováních. ' + story * 8),
         images=(ImageItem(media[3].id, repeat=True, alt_text='Fialový obdélník opakovaně'),))
    text('21 • Zkouška živé projekce',
         block('Spusťte projekci. Potom v editoru změňte tuto větu.'),
         block('Živý výstup se změní až po potvrzení do projekce.'),
         block('Vyzkoušejte šipky, černou obrazovku, návrat a ukončení podle ovládání aplikace.'))
    text('22 • Okno Zdrojové úseky',
         block('Na kartě Úseky otevřete Zobrazit všechny…'),
         block('Vyberte úsek podle názvu a přetáhněte jej myší na nové místo. Čára ukazuje místo vložení.'),
         block('Vyzkoušejte Zpět a také původní tlačítka Nahoru / Dolů.'))
    text('23 • Nastavení a výchozí hodnoty',
         block('Nastavení → Uložit defaultně: jedním tlačítkem vpravo uložíte ovládání, písmo, chování lišty a přímé úpravy obrázků.', size=28),
         block('Malé Uložit u fontu a velikosti platí jen pro nový obsah této prezentace. Zachová se při uložení souboru.', size=28),
         block('Nová prezentace používá globální výchozí hodnoty. Složky a kameru nastavujete v jejich vlastních dialozích.', size=28))
    text('24 • Konec ukázky', block('Další možnosti vyzkoušíte podle přiloženého návodu.'),
         block('Prezentaci si uložte pod vlastním názvem a upravujte její kopii.'),
         break_after=False)
    return Presentation(title='PresentationPresenter — průvodce funkcemi', sections=tuple(sections),
                        media=tuple(media), hall=OutputConfig(Aspect.STANDARD),
                        stream=OutputConfig(Aspect.WIDE, CameraRegion(.64, .62, .36, .38, .02)),
                        black_start=True, black_end=True, content_defaults=TextStyle(family='Calibri', size=36))


def main():
    target = Path(__file__).resolve().parents[1] / 'presentation' / 'Vzorova_prezentace.ppres'
    document = build()
    root = tk.Tk()
    root.withdraw()
    try:
        metrics = TkMetrics(root)
        plan = paginate(document, metrics)
        canvas = tk.Canvas(root)
        for slide in plan.slides:
            for output in ('hall', 'stream'):
                draw(canvas, slide, output, metrics, Typography(), scale=.5)
        counts = {s.title: sum(not slide.black and slide.section_id == s.id for slide in plan.slides)
                  for s in document.sections}
        for section in document.sections:
            assert counts[section.title] > 0, section.title
        for index in (5, 6, 18, 19):
            assert counts[document.sections[index].title] > 1
        # Validate the editable examples after switching either aspect ratio, too.
        for aspect in Aspect:
            paginate(replace(document, hall=replace(document.hall, aspect=aspect),
                             stream=replace(document.stream, aspect=aspect)), metrics)
        save(target, document)
        assert load(target) == document
        print(f'{target}\n{len(document.sections)} sections; {len(plan.slides)} slides; {len(document.media)} embedded rectangles')
        print(counts)
    finally:
        root.destroy()


if __name__ == '__main__':
    main()
