from gaia_agent.answer_rendering import render_final_answer


def test_count_rendering_uses_requested_unit_not_year_or_other_number():
    question='How many research reports were published in 2018?'
    assert render_final_answer(question,'In 2018 the team held 12 meetings and published 42 research reports.')=='42'
    assert render_final_answer(question,'The team published 42 research-reports.')=='42'
    assert render_final_answer(question,'42')=='42'


def test_ambiguous_uncertain_or_unrelated_numbers_are_not_extracted():
    question='How many research reports were published in 2018?'
    for answer in ('42 research reports or 43 research reports',
                   'About 42 research reports', 'Unable to verify; possibly 42 research reports',
                   '12 meetings in 2018', 'Not 42 research reports', '42 papers'):
        assert render_final_answer(question,answer)==answer
