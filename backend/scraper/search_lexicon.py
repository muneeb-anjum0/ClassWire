"""Natural-language grammar excluded from timetable entity similarity scoring.

These words describe how a user asks, combines, or modifies a timetable. They
are not evidence that a faculty member, course, or section was named. Keeping
the groups explicit makes additions reviewable and avoids mixing domain words
such as "software" or "engineering" into a generic stopword list.
"""

REQUEST_WORDS = frozenset({
    "ask", "asked", "asking", "asks", "browse", "browsed", "browses", "browsing",
    "check", "checked", "checking", "checks", "display", "displayed", "displaying",
    "displays", "fetch", "fetched", "fetches", "fetching", "find", "finding", "finds",
    "found", "get", "gets", "getting", "give", "gives", "given", "giving", "list",
    "listed", "listing", "lists", "load", "loaded", "loading", "loads", "locate",
    "located", "locates", "locating", "look", "looked", "looking", "looks", "provide",
    "provided", "provides", "providing", "query", "queried", "queries", "querying",
    "retrieve", "retrieved", "retrieves", "retrieving", "search", "searched", "searches",
    "searching", "see", "seeing", "seen", "sees", "show", "showed", "showing", "shown",
    "shows", "tell", "telling", "tells", "view", "viewed", "viewing", "views",
})

DESIRE_WORDS = frozenset({
    "aim", "aimed", "aiming", "aims", "desire", "desired", "desires", "desiring",
    "hope", "hoped", "hopes", "hoping", "intend", "intended", "intending", "intends",
    "like", "liked", "likes", "liking", "need", "needed", "needing", "needs", "prefer",
    "preferred", "preferring", "prefers", "require", "required", "requires", "requiring",
    "try", "tried", "tries", "trying", "want", "wanted", "wanting", "wants", "wish",
    "wished", "wishes", "wishing", "would",
})

ENROLLMENT_WORDS = frozenset({
    "add", "added", "adding", "adds", "admit", "admits", "admitted", "admitting", "attend",
    "attended", "attending", "attends", "belong", "belonged", "belonging", "belongs", "choose",
    "chooses", "chosen", "choosing", "drop", "dropped", "dropping", "drops", "enroll", "enrolled",
    "enrolling", "enrolls", "exclude", "excluded", "excludes", "excluding", "include", "included",
    "includes", "including", "join", "joined", "joining", "joins", "keep", "keeping", "keeps", "kept",
    "omit", "omits", "omitted", "omitting", "pick", "picked", "picking", "picks", "register",
    "registered", "registering", "registers", "remove", "removed", "removes", "removing", "retain",
    "retained", "retaining", "retains", "select", "selected", "selecting", "selects", "skip",
    "skipped", "skipping", "skips", "study", "studied", "studies", "studying", "take", "taken",
    "takes", "taking", "took", "use", "used", "uses", "using",
})

CONNECTOR_WORDS = frozenset({
    "additionally", "after", "afterward", "afterwards", "again", "against", "along",
    "alongside", "also", "although", "and", "apart", "as", "beside", "besides", "but",
    "consequently", "either", "else", "except", "finally", "first", "following", "for",
    "from", "furthermore", "hence", "however", "instead", "last", "later", "likewise",
    "meanwhile", "moreover", "neither", "next", "nor", "notwithstanding", "once", "only",
    "or", "otherwise", "plus", "rather", "second", "similarly", "since", "so", "subsequently",
    "than", "then", "thereafter", "therefore", "though", "together", "too", "unless", "versus",
    "upon", "via", "whereas", "while", "with", "within", "without", "yet",
})

AUXILIARY_WORDS = frozenset({
    "am", "are", "be", "became", "become", "becomes", "been", "being", "can", "cannot",
    "could", "did", "do", "does", "doing", "done", "had", "has", "have", "having", "is",
    "may", "might", "must", "shall", "should", "was", "were", "will", "wont", "would",
    "arent", "cant", "couldnt", "didnt", "doesnt", "dont", "hadnt", "hasnt", "havent",
    "isnt", "mustnt", "neednt", "shouldnt", "wasnt", "werent", "wouldnt",
})

REFERENCE_WORDS = frozenset({
    "about", "all", "another", "any", "anybody", "anyone", "anything", "both", "complete",
    "current", "each", "either", "entire", "every", "everybody", "everyone", "everything",
    "few", "full", "here", "hers", "herself", "him", "himself", "it", "itself", "its", "mine",
    "most", "my", "myself", "none", "other", "others", "ours", "ourselves", "own", "same",
    "several", "some", "somebody", "someone", "something", "specific", "that", "the", "their",
    "theirs", "them", "themselves", "these", "they", "this", "those", "us", "we", "whatever",
    "whichever", "which", "whole", "whoever", "whomever", "whose", "you", "your", "yours",
    "yourself", "yourselves",
})

RELATION_WORDS = frozenset({
    "assigned", "assigns", "conduct", "conducted", "conducting", "conducts", "faculty", "handled",
    "handles", "handling", "instruct", "instructed", "instructing", "instructor", "instructors",
    "lecture", "lecturer", "lecturers", "lectures", "professor", "professors", "section", "sections",
    "semester", "semesters", "sir", "student", "students", "teach", "teacher", "teachers", "teaches",
    "teaching", "taught", "under",
})

CONVERSATIONAL_WORDS = frozenset({
    "actually", "basically", "certainly", "clearly", "definitely", "exactly", "frankly", "hey", "hi",
    "hopefully", "ideally", "just", "kindly", "maybe", "obviously", "okay", "ok", "perhaps", "please",
    "possibly", "probably", "really", "seriously", "simply", "surely", "thank", "thanks", "wanted",
    "wonder", "wondered", "wondering",
})

QUESTION_WORDS = frozenset({
    "how", "what", "whatever", "when", "whenever", "where", "wherever", "whether", "which",
    "whichever", "who", "whoever", "whom", "whose", "why",
})

POSITION_WORDS = frozenset({
    "above", "across", "around", "before", "behind", "below", "between", "beyond", "by", "during",
    "inside", "into", "near", "nearby", "off", "onto", "outside", "over", "past", "through",
    "throughout", "toward", "towards", "underneath", "until", "up", "via",
})

# These smaller semantic sets drive the custom-schedule planner. They are kept
# separate from QUERY_GRAMMAR_WORDS because they carry meaning even though they
# must never be treated as evidence for a course or faculty name.
ADDITIVE_SCOPE_WORDS = frozenset({
    "add", "added", "adding", "adds", "admit", "admitted", "attend", "attended",
    "attending", "attends", "choose", "chooses", "chosen", "choosing", "enroll",
    "enrolled", "enrolling", "enrolls", "include", "included", "includes", "including",
    "join", "joined", "joining", "joins", "keep", "keeping", "keeps", "kept", "pick",
    "picked", "picking", "picks", "register", "registered", "registering", "registers",
    "retain", "retained", "retaining", "retains", "select", "selected", "selecting",
    "selects", "study", "studied", "studies", "studying", "take", "taken", "takes",
    "taking", "took", "use", "used", "uses", "using",
})

COURSE_SECTION_CONNECTORS = frozenset({
    "", "at", "belongingto", "by", "conductedby", "for", "from", "fromsection", "in",
    "insection", "inside", "offeredby", "of", "section", "sectionof", "through", "under",
    "via", "with", "withsection", "within",
})

HOME_SECTION_PREFIXES = frozenset({
    "classof", "classesof", "currentlyin", "iamfrom", "iamin", "iamtakingallclasseswith",
    "iamtakingeveryclasswith", "ibelongto", "ienrolledin", "imin", "imfrom", "imregisteredwith",
    "itakeallclasseswith", "itakeeveryclasswith", "mybaseis", "myclassis", "mycoresectionis",
    "mysectionis", "mysemesteris", "registeredwith", "scheduleof", "studentin", "studentof",
    "studyingin", "takingallclasseswith", "takingeveryclasswith", "timetableof",
})

QUERY_GRAMMAR_WORDS = frozenset().union(
    REQUEST_WORDS,
    DESIRE_WORDS,
    ENROLLMENT_WORDS,
    CONNECTOR_WORDS,
    AUXILIARY_WORDS,
    REFERENCE_WORDS,
    RELATION_WORDS,
    CONVERSATIONAL_WORDS,
    QUESTION_WORDS,
    POSITION_WORDS,
)
