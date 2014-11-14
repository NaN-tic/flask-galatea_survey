from flask import Blueprint, render_template, current_app, abort, g, \
    url_for, request, session, flash
from galatea.tryton import tryton
from flask.ext.babel import gettext as _, lazy_gettext
from flask.ext.paginate import Pagination
from flask.ext.wtf import Form
from wtforms import BooleanField, DateField, DateTimeField, FloatField, \
    IntegerField, SelectField, TextAreaField, TextField, PasswordField, \
    validators
from htmlmin.decorator import htmlmin

survey = Blueprint('survey', __name__, template_folder='templates')

DISPLAY_MSG = lazy_gettext('Displaying <b>{start} - {end}</b> of <b>{total}</b>')

GALATEA_WEBSITE = current_app.config.get('TRYTON_GALATEA_SITE')
LIMIT = current_app.config.get('TRYTON_PAGINATION_SURVEY_LIMIT', 20)

Survey = tryton.pool.get('survey.survey')

SURVEY_FIELD_NAMES = ['name', 'code', 'slug', 'esale_description']
SURVEY_EXCLUDE_DATA = ['csrf_token']


class BaseForm(Form):
    """ A Base Form"""

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        return True

    def reset(self):
        pass


@survey.route("/<slug>", methods=["GET", "POST"], endpoint="survey")
@tryton.transaction()
@htmlmin
def survey_detail(lang, slug):
    '''Survey Detail'''

    domain = [
        ('slug', '=', slug),
        ('websites', 'in', [GALATEA_WEBSITE]),
        ('active', '=', True),
        ('esale', '=', True),
        ]
    if not session.get('logged_in'):
        domain.append(('login', '=', False))
    if not session.get('manager'):
        domain.append(('manager', '=', False))

    surveys = Survey.search(domain, limit=1)

    if not surveys:
        abort(404)
    survey, = surveys

    survey_form = Survey.galatea_survey_form(survey)
    total_steps = len(survey_form.keys())

    for step in survey_form:
        for field in survey_form[step]['fields']:
            name = field['name']
            label = field['label']
            description = field['help']
            default_value = field.get('default_value', None)
            
            field_validators = []
            if field['required']:
                field_validators.append(validators.Required())
            if field['email']:
                field_validators.append(validators.Email())
            if field['url']:
                field_validators.append(validators.URL())

            if field['type_'] == 'boolean':
                setattr(BaseForm, name, BooleanField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'date':
                setattr(BaseForm, name, DateField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'datetime':
                setattr(BaseForm, name, DateTimeField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'float':
                setattr(BaseForm, name, FloatField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'integer':
                setattr(BaseForm, name, IntegerField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'numeric':
                setattr(BaseForm, name, IntegerField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'selection':
                choices = []
                for option in field['selection'].split('\n'):
                    choices.append(option.split(':'))
                setattr(BaseForm, name, SelectField(
                    label, description=description, default=default_value,
                    choices=choices, validators=field_validators))
            elif field['type_'] == 'char' and field['textarea']:
                setattr(BaseForm, name, TextAreaField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            elif field['type_'] == 'char' and field['password']:
                setattr(BaseForm, name, PasswordField(
                    label, description=description, default=default_value,
                    validators=field_validators))
            else:
                setattr(BaseForm, name, TextField(
                    label, description=description, default=default_value,
                    validators=field_validators))

    breadcrumbs = [{
        'slug': url_for('.surveys', lang=g.language),
        'name': _('Forms'),
        }, {
        'slug': url_for('.survey', lang=g.language, slug=survey.slug),
        'name': survey.name,
        }]

    form = BaseForm(request.form)
    if form.validate_on_submit():
        data = {}
        for k, v in request.form.iteritems():
            if k not in SURVEY_EXCLUDE_DATA:
                data[k] = v
        result = Survey.save_data(survey, data)

        if result:
            # ok. render thanks template
            return render_template('survey-thanks.html',
                    breadcrumbs=breadcrumbs,
                    survey=survey,
                    )
        else:
            flash(_('An error occured when save data. Not send form. ' \
                'Repeat or contact us'), 'danger')

    return render_template('survey.html',
            breadcrumbs=breadcrumbs,
            survey=survey,
            total_steps=total_steps,
            survey_form=survey_form,
            form=form,
            )

@survey.route("/", endpoint="surveys")
@tryton.transaction()
def survey_list(lang):
    '''Surveys'''

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    domain = [
        ('websites', 'in', [GALATEA_WEBSITE]),
        ('active', '=', True),
        ('esale', '=', True),
        ]
    if not session.get('logged_in'):
        domain.append(('login', '=', False))
    if not session.get('manager'):
        domain.append(('manager', '=', False))

    total = Survey.search_count(domain)
    offset = (page-1)*LIMIT

    order = [
        ('id', 'DESC'),
        ]
    surveys = Survey.search_read(
        domain, offset, LIMIT, order, SURVEY_FIELD_NAMES)

    pagination = Pagination(
        page=page, total=total, per_page=LIMIT, display_msg=DISPLAY_MSG, bs_version='3')

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.surveys', lang=g.language),
        'name': _('Forms'),
        }]

    return render_template('surveys.html',
            breadcrumbs=breadcrumbs,
            pagination=pagination,
            surveys=surveys,
            )
