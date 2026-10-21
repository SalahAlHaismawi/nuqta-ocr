from PIL import Image

from nuqta import is_page, looped, prepare, read_fields, trim_loops
from nuqta.preprocess import TRAIN_PIXELS, plain
from nuqta.text import clean


def test_page_rule_enlarges_small_pages_only():
    page = Image.new("RGB", (612, 792), "white")  # a 72-dpi PDF page render
    big = prepare(page)
    assert is_page(page) and abs(big.width * big.height - TRAIN_PIXELS) / TRAIN_PIXELS < 0.01
    line = Image.new("RGB", (1200, 80), "white")  # a text line crop: never enlarged
    assert not is_page(line) and prepare(line).size == line.size
    word = Image.new("RGB", (300, 120), "white")
    assert prepare(word).size == word.size


def test_cap_at_training_size():
    huge = Image.new("RGB", (4000, 3000), "white")
    for im in (prepare(huge), plain(huge)):
        assert im.width * im.height <= TRAIN_PIXELS * 1.01


def test_loops():
    page = "السطر الأول من الصفحة\n" + "١ | ١ | " * 200
    assert looped(page) and len(trim_loops(page)) < 100
    assert not looped("نص عادي بلا تكرار " * 3)
    assert trim_loops("P<UTO<<<<<<<<<<<<<<<<<<<<<<") == "P<UTO<<<<<<<<<<<<<<<<<<<<<<"  # MRZ filler is kept


def test_clean():
    assert clean("<think>x</think>```markdown\n# عنوان\n```") == "# عنوان"


def test_mrz_icao_specimen():
    text = "PASSPORT\nP<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10"
    m = read_fields(text)["mrz"]
    assert m["valid"] and m["number"] == "L898902C3" and m["surname"] == "ERIKSSON"


def test_trim_loops_keeps_real_repeats_and_cuts_runaways():
    from nuqta.text import looped, trim_loops
    row = "<tr><td>قلم</td><td>1</td><td>5</td></tr>"
    for keep in ("<table>" + row * 9 + "</table>\nالمجموع 45",            # identical table rows
                 "الاسم: ...................................... التاريخ: ____________________",  # form lines
                 "\n".join(["يا ليلُ الصبُّ متى غدُه أقيامُ الساعةِ موعدُهُ"] * 4)):  # refrain
        assert trim_loops(keep) == keep and not looped(keep)
    runaway = "مقدمة النص. " + "وهذا مثال متكرر " * 60
    assert looped(runaway) and len(trim_loops(runaway)) < 60
