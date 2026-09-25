from scraper.search_lexicon import (
    ADDITIVE_SCOPE_WORDS,
    COURSE_SECTION_CONNECTORS,
    HOME_SECTION_PREFIXES,
    QUERY_GRAMMAR_WORDS,
)


def test_query_grammar_lexicon_covers_major_language_families_and_inflections():
    expected = {
        "asking", "retrieved", "wishes", "taking", "registered", "including",
        "alongside", "wouldnt", "ourselves", "professors", "wondering", "wherever",
        "throughout",
    }

    assert len(QUERY_GRAMMAR_WORDS) >= 450
    assert expected <= QUERY_GRAMMAR_WORDS


def test_query_grammar_lexicon_does_not_swallow_core_timetable_entities():
    domain_words = {
        "software", "construction", "development", "quality", "engineering",
        "testing", "networks", "qasim", "wahab",
    }

    assert QUERY_GRAMMAR_WORDS.isdisjoint(domain_words)


def test_custom_schedule_semantic_sets_cover_varied_natural_phrasing():
    assert {"taking", "enrolled", "registering", "retaining", "using"} <= ADDITIVE_SCOPE_WORDS
    assert {"with", "from", "under", "via", "offeredby", "conductedby"} <= COURSE_SECTION_CONNECTORS
    assert {"iamfrom", "studentof", "currentlyin", "mysectionis"} <= HOME_SECTION_PREFIXES
