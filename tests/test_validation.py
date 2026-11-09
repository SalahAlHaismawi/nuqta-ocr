from nuqta.text import counting_sequence, validate_text


def test_counting_sequence_detects_a_loop_but_not_a_table():
    assert counting_sequence(' '.join(str(n) for n in range(1, 30)))
    assert not counting_sequence('١ ٢ ٣ ثم كلام')
    assert not counting_sequence('القلم 1 والكتاب 2 والورق 3')
    assert not counting_sequence(' '.join(f'{n}. item' for n in range(1, 20)))


def test_validate_text_reports_repetition_and_dominance():
    assert 'repeated output' in validate_text('نص ' + 'أ' * 300)
    assert 'one character dominates' in validate_text('أ' * 200)
    assert validate_text('نص عربي سليم') == []
    assert validate_text('الاسم: ' + '.' * 60) == []
