import unittest

from twenty_bits.name_reference_audit import referenced_names, audit_name_references


class NameReferenceTests(unittest.TestCase):
    def test_malformed_lists_are_visible_without_fuzzy_matching(self):
        names={"adult_female_parrot","adult_female_squirrel"}
        self.assertEqual(referenced_names("(adult_female_parrot OR adult_female_squirrel",names),names)
        self.assertEqual(referenced_names("adult_female_parrot_suffix",names),set())

    def test_literal_names_and_item_operator_have_distinct_roles(self):
        self.assertEqual(referenced_names('item == "red fox"',{"item","red fox"}),{"red fox"})
        self.assertEqual(referenced_names('item == "item"',{"item"}),{"item"})

    def test_invalid_identity_questions_keep_their_error_and_support(self):
        turns=[{"raw_action":"ASK: adult_female_parrot","is_question":True,"invalid":True,"posterior_before":[.5,.5],"error":"unknown"},
               {"raw_action":"ASK: adult_female_squirrel","is_question":True,"invalid":True,"posterior_before":[.5,.5],"error":"unknown"}]
        game={"game_id":"g","n":2,"kind":"train","update":1,"turns":turns}
        records={"g":{"world":{"names":["adult_female_parrot","adult_female_squirrel"]}}}
        report=audit_name_references([game],records)
        self.assertEqual(report["counts"]["invalid_bare_candidate_name_questions"],2)
        self.assertEqual(report["counts"]["consecutive_different_bare_names"],1)
        self.assertFalse(report["primary_scoring_changed"])
