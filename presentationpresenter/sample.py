from .domain import Presentation, TextSection, TextBlock, TextRun, TextStyle, BlockKind

def sample_document():
    return Presentation(title='Ukázková prezentace', sections=(
        TextSection('Vítejte', (
            TextBlock((TextRun('PresentationPresenter', TextStyle(bold=True)), TextRun(' — samostatná příprava prezentací.'))),
            TextBlock((TextRun('Strukturované odstavce a odrážky'),), BlockKind.BULLET),
            TextBlock((TextRun('Nezávislý sál a stream', TextStyle(italic=True, color='#ffd166')),), BlockKind.BULLET),
            TextBlock((TextRun('Text nad rezervou kamery využívá celou šířku. Vedle kamery se řádky zúží. ' * 12),)),
            TextBlock((TextRun('Tato dlouhá odrážka má společný obsah pro oba výstupy. ' * 30, TextStyle(underline=True)),), BlockKind.BULLET),
        ), reference='Ukázka PP2'),
    ))
