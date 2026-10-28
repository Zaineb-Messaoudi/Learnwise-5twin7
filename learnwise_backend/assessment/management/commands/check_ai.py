"""
Vérifie en une commande que l'IA est bien configurée :

    python manage.py check_ai                 # fait UN vrai appel et affiche deux questions d'exemple
    python manage.py check_ai --list-models   # liste les modèles que votre clé peut utiliser

La configuration vient du fichier .env (Groq ou Ollama). En cas de problème, la commande affiche
le même message que verrait un professeur.
"""
from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError

from assessment import ai_client


class Command(BaseCommand):
    help = "Teste l'IA (Groq ou Ollama) : un vrai appel, ou la liste des modèles disponibles."

    def add_arguments(self, parser):
        parser.add_argument(
            '--list-models', action='store_true',
            help='Affiche les modèles utilisables avec la clé actuelle, au lieu de générer des questions.',
        )

    def handle(self, *args, **options):
        if options['list_models']:
            return self.show_models()
        return self.try_generation()

    # -- --list-models ------------------------------------------------------
    def show_models(self):
        try:
            provider, models = ai_client.list_models()
        except ai_client.GenerationError as error:
            raise CommandError(error.user_message)

        env_name = 'GROQ_MODEL' if provider.name == 'groq' else 'OLLAMA_MODEL'
        self.stdout.write(f'Provider: {provider.name} | Current {env_name}: {provider.model}\n')
        if not models:
            raise CommandError('No usable model was returned for this account.')
        for model in models:
            mark = '  <- current (OK)' if model == provider.model else ''
            self.stdout.write(f'  {model}{mark}')
        if provider.model not in models:
            self.stdout.write(self.style.WARNING(
                f'\n{env_name}="{provider.model}" is NOT in this list. '
                f'Pick one of the models above and set {env_name}=... in your .env file, then restart.'
            ))

    # -- appel réel ------------------------------------------------------------
    def try_generation(self):
        try:
            provider = ai_client.current_provider()
        except ai_client.GenerationError as error:
            raise CommandError(error.user_message)
        self.stdout.write(f'Provider: {provider.name} | Model: {provider.model}')

        # Faux cours : cette commande n'utilise pas la base de données.
        course = SimpleNamespace(title='Photosynthesis basics', level='Beginner', language='English')
        try:
            questions = ai_client.generate_questions(
                source_text='Photosynthesis in plants', course=course,
                kind='quiz', count=2, difficulty='easy',
            )
        except ai_client.GenerationError as error:
            if error.status in (400, 404):  # le plus souvent : modèle retiré ou inconnu
                self.stderr.write('Tip: run "python manage.py check_ai --list-models" to see the models your key can use.')
            raise CommandError(error.user_message)

        for number, question in enumerate(questions, start=1):
            self.stdout.write(f'\nQ{number}. {question["prompt"]}')
            for index, choice in enumerate(question['choices']):
                mark = '  <- correct' if index == question['correct_index'] else ''
                self.stdout.write(f'   {index + 1}. {choice["text"]}{mark}')
        self.stdout.write(self.style.SUCCESS(f'\nThe AI works: {provider.name} / {provider.model} answered correctly.'))