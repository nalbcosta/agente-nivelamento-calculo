from app.schemas.request import NivelamentoRequest
from app.schemas.response import NivelamentoResponse

REQUIRED_TOPICS = {
	"algebra_basica": "Algebra basica",
	"funcoes": "Funcoes",
	"trigonometria": "Trigonometria",
}


def avaliar_nivelamento(payload: NivelamentoRequest) -> NivelamentoResponse:
	normalized = {topic.strip().lower() for topic in payload.known_topics}
	missing = [
		label
		for key, label in REQUIRED_TOPICS.items()
		if key not in normalized and label.lower() not in normalized
	]

	is_ready = len(missing) == 0
	if is_ready:
		support_text = (
			"Voce parece pronto para iniciar Calculo I. "
			"Vamos avancar para limites e interpretacao grafica."
		)
	else:
		support_text = (
			"Antes de comecar Calculo I, revise: "
			+ ", ".join(missing)
			+ ". Foco em exemplos curtos e exercicios basicos."
		)

	return NivelamentoResponse(
		is_ready=is_ready,
		missing_prerequisites=missing,
		support_text=support_text,
	)
