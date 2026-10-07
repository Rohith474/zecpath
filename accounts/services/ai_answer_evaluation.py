from decimal import Decimal, ROUND_HALF_UP

from accounts.models import AIAnswerEvaluation


class AIAnswerEvaluationService:

    RELEVANCE_WEIGHT = Decimal("0.40")
    COMPLETENESS_WEIGHT = Decimal("0.30")
    KEYWORD_WEIGHT = Decimal("0.30")

    CATEGORY_KEYWORDS = {
        "Introduction": [
            "computer",
            "science",
            "graduate",
            "developer",
            "student",
            "background",
            "interested",
        ],
        "Experience": [
            "experience",
            "worked",
            "project",
            "company",
            "developer",
            "responsibility",
            "developed",
        ],
        "Skills": [
            "python",
            "django",
            "java",
            "javascript",
            "sql",
            "api",
            "rest",
            "machine learning",
            "programming",
        ],
        "Availability": [
            "available",
            "immediately",
            "join",
            "week",
            "month",
            "start",
            "notice",
            "constraints",
        ],
        "Salary": [
            "salary",
            "lpa",
            "compensation",
            "expected",
            "inr",
            "pay",
            "package",
        ],
    }

    def __init__(self, answer):
        self.answer = answer

    def _round_score(self, value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def get_category(self):
        question = self.answer.question_text.lower()

        if any(
            word in question
            for word in ["tell me about yourself", "introduce yourself"]
        ):
            return "Introduction"

        if any(
            word in question
            for word in ["experience", "previous work"]
        ):
            return "Experience"

        if any(
            word in question
            for word in ["technical skills", "skills"]
        ):
            return "Skills"

        if any(
            word in question
            for word in ["available", "availability", "join"]
        ):
            return "Availability"

        if any(
            word in question
            for word in ["salary", "compensation"]
        ):
            return "Salary"

        return "Introduction"

    def calculate_relevance(self):
        category = self.get_category()
        keywords = self.CATEGORY_KEYWORDS.get(category, [])
        answer_text = self.answer.answer_text.lower()

        if not answer_text or not keywords:
            return Decimal("0.00")

        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword in answer_text
        ]

        score = (
            Decimal(len(matched_keywords))
            / Decimal(len(keywords))
        ) * Decimal("100")

        return self._round_score(min(Decimal("100"), score))

    def calculate_completeness(self):
        answer = self.answer.answer_text.strip()

        if not answer:
            return Decimal("0.00")

        word_count = len(answer.split())

        if word_count >= 30:
            return Decimal("100.00")

        if word_count >= 20:
            return Decimal("85.00")

        if word_count >= 10:
            return Decimal("70.00")

        if word_count >= 5:
            return Decimal("50.00")

        return Decimal("25.00")

    def calculate_keyword_match(self):
        category = self.get_category()
        keywords = self.CATEGORY_KEYWORDS.get(category, [])
        answer_text = self.answer.answer_text.lower()

        if not keywords or not answer_text:
            return Decimal("0.00"), []

        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword in answer_text
        ]

        score = (
            Decimal(len(matched_keywords))
            / Decimal(len(keywords))
        ) * Decimal("100")

        return (
            self._round_score(min(Decimal("100"), score)),
            matched_keywords,
        )

    def calculate_final_score(
        self,
        relevance_score,
        completeness_score,
        keyword_score,
    ):
        score = (
            relevance_score * self.RELEVANCE_WEIGHT
            + completeness_score * self.COMPLETENESS_WEIGHT
            + keyword_score * self.KEYWORD_WEIGHT
        )

        return self._round_score(
            min(Decimal("100"), score)
        )

    def evaluate(self):
        relevance_score = self.calculate_relevance()

        completeness_score = self.calculate_completeness()

        keyword_score, matched_keywords = self.calculate_keyword_match()

        final_score = self.calculate_final_score(
            relevance_score,
            completeness_score,
            keyword_score,
        )

        confidence = self._round_score(
            (
                relevance_score
                + completeness_score
                + keyword_score
            ) / Decimal("3")
        )

        annotations = {
            "category": self.get_category(),
            "matched_keywords": matched_keywords,
            "weights": {
                "relevance": "40%",
                "completeness": "30%",
                "keyword_match": "30%",
            },
        }

        evaluation, created = AIAnswerEvaluation.objects.update_or_create(
            answer=self.answer,
            defaults={
                "relevance_score": relevance_score,
                "completeness_score": completeness_score,
                "keyword_score": keyword_score,
                "final_score": final_score,
                "confidence": confidence,
                "annotations": annotations,
            },
        )

        return evaluation