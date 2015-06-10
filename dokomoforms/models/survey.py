"""Survey models."""

from collections import OrderedDict

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import relationship
from sqlalchemy.ext.orderinglist import ordering_list

from dokomoforms.models import util, Base, node_type_enum
from dokomoforms.exc import NoSuchBucketTypeError


class Survey(Base):
    __tablename__ = 'survey'

    id = util.pk()
    title = sa.Column(
        pg.TEXT,
        sa.CheckConstraint("title != ''", name='non_empty_survey_title'),
        nullable=False,
    )
    default_language = sa.Column(
        pg.TEXT,
        sa.CheckConstraint(
            "default_language != ''", name='non_empty_default_language'
        ),
        nullable=False,
        server_default='English',
    )
    translations = sa.Column(
        pg.json.JSONB, nullable=False, server_default='{}'
    )
    # TODO: expand upon this
    version = sa.Column(sa.Integer, nullable=False, server_default='1')
    # ODOT
    creator_id = sa.Column(
        pg.UUID, util.fk('survey_creator.id'), nullable=False
    )
    survey_metadata = sa.Column(
        pg.json.JSONB, nullable=False, server_default='{}'
    )
    created_on = sa.Column(
        sa.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    nodes = relationship(
        'SurveyNode',
        order_by='SurveyNode.node_number',
        collection_class=ordering_list('node_number'),
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    last_update_time = util.last_update_time()

    __table_args__ = (
        sa.UniqueConstraint(
            'title', 'creator_id', name='unique_survey_title_per_user'
        ),
    )

    def _asdict(self) -> OrderedDict:
        return OrderedDict((
            ('id', self.id),
            ('deleted', self.deleted),
            ('title', self.title),
            ('default_language', self.default_language),
            ('translations', self.translations),
            ('version', self.version),
            ('creator', self.creator.name),
            ('metadata', self.survey_metadata),
            ('created_on', self.created_on),
            ('last_update_time', self.last_update_time),
            ('nodes', self.nodes),
        ))


_sub_survey_nodes = sa.Table(
    'sub_survey_nodes',
    Base.metadata,
    sa.Column('sub_survey_id', pg.UUID, sa.ForeignKey('sub_survey.id')),
    sa.Column('survey_node_id', pg.UUID, sa.ForeignKey('survey_node.id')),
)


class SubSurvey(Base):
    __tablename__ = 'sub_survey'

    id = util.pk()
    sub_survey_number = sa.Column(sa.Integer, nullable=False)
    parent_survey_node_id = sa.Column(pg.UUID, nullable=False)
    parent_node_id = sa.Column(pg.UUID, nullable=False)
    parent_type_constraint = sa.Column(node_type_enum, nullable=False)
    buckets = relationship(
        'Bucket',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    repeatable = sa.Column(sa.Boolean, nullable=False, server_default='false')
    nodes = relationship(
        'SurveyNode',
        secondary=_sub_survey_nodes,
        order_by='SurveyNode.node_number',
        collection_class=ordering_list('node_number'),
        cascade='all, delete-orphan',
        passive_deletes=True,
        single_parent=True,
    )

    __table_args__ = (
        sa.UniqueConstraint('id', 'parent_type_constraint'),
        sa.UniqueConstraint('parent_survey_node_id', 'parent_node_id'),
        sa.ForeignKeyConstraint(
            ['parent_survey_node_id', 'parent_type_constraint',
                'parent_node_id'],
            ['survey_node.id', 'survey_node.type_constraint',
                'survey_node.node_id']
        ),
    )

    def _asdict(self) -> OrderedDict:
        return OrderedDict((
            ('deleted', self.deleted),
            ('buckets', [bucket.bucket for bucket in self.buckets]),
            ('repeatable', self.repeatable),
            ('nodes', self.nodes),
        ))


bucket_type_enum = sa.Enum(
    'integer', 'decimal', 'date', 'time', 'multiple_choice',
    name='bucket_type_name',
    inherit_schema=True,
    metadata=Base.metadata,
)


class Bucket(Base):
    __abstract__ = True

    last_update_time = util.last_update_time()

    def _default_asdict(self) -> OrderedDict:
        return OrderedDict((
            ('id', self.id),
            ('bucket_type', self.bucket_type),
            ('bucket', self.bucket),
        ))


def _bucket_type_check_constraint():
    return sa.CheckConstraint(
        'bucket_type::TEXT = sub_survey_parent_type_constraint::TEXT'
    )


def _bucket_fk_constraint():
    return sa.ForeignKeyConstraint(
        ['sub_survey_id', 'sub_survey_parent_type_constraint'],
        ['sub_survey.id', 'sub_survey.parent_type_constraint']
    )


def _bucket_exclude_constraint():
    return pg.ExcludeConstraint(('sub_survey_id', '='), ('bucket', '&&'))


class IntegerBucket(Bucket):
    __tablename__ = 'bucket_integer'

    id = util.pk()
    bucket_type = sa.Column(bucket_type_enum, nullable=False)
    sub_survey_id = sa.Column(pg.UUID, nullable=False)
    sub_survey_parent_type_constraint = sa.Column(
        node_type_enum, nullable=False
    )
    bucket = sa.Column(pg.INT4RANGE, nullable=False)

    __table_args__ = (
        _bucket_type_check_constraint(),
        _bucket_fk_constraint(),
        _bucket_exclude_constraint(),
    )

    def _asdict(self) -> OrderedDict:
        return super()._default_asdict()


class DecimalBucket(Bucket):
    __tablename__ = 'bucket_decimal'

    id = util.pk()
    bucket_type = sa.Column(bucket_type_enum, nullable=False)
    sub_survey_id = sa.Column(pg.UUID, nullable=False)
    sub_survey_parent_type_constraint = sa.Column(
        node_type_enum, nullable=False
    )
    bucket = sa.Column(pg.NUMRANGE, nullable=False)

    __table_args__ = (
        _bucket_type_check_constraint(),
        _bucket_fk_constraint(),
        _bucket_exclude_constraint(),
    )

    def _asdict(self) -> OrderedDict:
        return super()._default_asdict()


class DateBucket(Bucket):
    __tablename__ = 'bucket_date'

    id = util.pk()
    bucket_type = sa.Column(bucket_type_enum, nullable=False)
    sub_survey_id = sa.Column(pg.UUID, nullable=False)
    sub_survey_parent_type_constraint = sa.Column(
        node_type_enum, nullable=False
    )
    bucket = sa.Column(pg.DATERANGE, nullable=False)

    __table_args__ = (
        _bucket_type_check_constraint(),
        _bucket_fk_constraint(),
        _bucket_exclude_constraint(),
    )

    def _asdict(self) -> OrderedDict:
        return super()._default_asdict()


class TimeBucket(Bucket):
    __tablename__ = 'bucket_time'

    id = util.pk()
    bucket_type = sa.Column(bucket_type_enum, nullable=False)
    sub_survey_id = sa.Column(pg.UUID, nullable=False)
    sub_survey_parent_type_constraint = sa.Column(
        node_type_enum, nullable=False
    )
    bucket = sa.Column(pg.TSTZRANGE, nullable=False)

    __table_args__ = (
        _bucket_type_check_constraint(),
        _bucket_fk_constraint(),
        _bucket_exclude_constraint(),
    )

    def _asdict(self) -> OrderedDict:
        return super()._default_asdict()


class MultipleChoiceBucket(Bucket):
    __tablename__ = 'bucket_multiple_choice'

    id = util.pk()
    bucket_type = sa.Column(bucket_type_enum, nullable=False)
    sub_survey_id = sa.Column(pg.UUID, nullable=False)
    sub_survey_parent_type_constraint = sa.Column(
        node_type_enum, nullable=False
    )
    bucket = sa.Column(pg.UUID, nullable=False)
    parent_survey_node_id = sa.Column(pg.UUID, nullable=False)
    parent_node_id = sa.Column(pg.UUID, nullable=False)

    __table_args__ = (
        _bucket_type_check_constraint(),
        _bucket_fk_constraint(),
        sa.ForeignKeyConstraint(
            ['bucket', 'parent_node_id'],
            ['choice.id', 'choice.question_id']
        ),
        sa.ForeignKeyConstraint(
            ['parent_survey_node_id', 'parent_node_id'],
            ['sub_survey.parent_survey_node_id', 'sub_survey.parent_node_id']
        ),
    )

    def _asdict(self) -> OrderedDict:
        return super()._default_asdict()


BUCKET_TYPES = {
    'integer': IntegerBucket,
    'decimal': DecimalBucket,
    'date': DateBucket,
    'time': TimeBucket,
    'multiple_choice': MultipleChoiceBucket,
}


def construct_bucket(*, bucket_type: str, **kwargs) -> Bucket:
    try:
        return BUCKET_TYPES[bucket_type](**kwargs)
    except KeyError:
        raise NoSuchBucketTypeError(bucket_type)


class SurveyNode(Base):
    __tablename__ = 'survey_node'

    id = util.pk()
    node_number = sa.Column(sa.Integer, nullable=False)
    node_id = sa.Column(pg.UUID, nullable=False)
    type_constraint = sa.Column(node_type_enum, nullable=False)
    node = relationship('Node')
    root_survey_id = sa.Column(pg.UUID, util.fk('survey.id'))
    nodes = relationship(
        'SubSurvey',
        order_by='SubSurvey.sub_survey_number',
        collection_class=ordering_list('sub_survey_number'),
        cascade='all, delete-orphan',
        passive_deletes=True,
        single_parent=True,
    )
    required = sa.Column(sa.Boolean, nullable=False, server_default='false')
    allow_dont_know = sa.Column(
        sa.Boolean, nullable=False, server_default='false'
    )
    logic = sa.Column(pg.json.JSONB, nullable=False, server_default='{}')

    __table_args__ = (
        sa.UniqueConstraint('id', 'node_id', 'type_constraint'),
        sa.ForeignKeyConstraint(
            ['node_id', 'type_constraint'],
            ['node.id', 'node.type_constraint']
        ),
    )

    def _asdict(self) -> OrderedDict:
        result = self.node._asdict()
        result['logic'].update(self.logic)
        result['node_id'] = result.pop('id')
        result['deleted'] = self.deleted
        result['required'] = self.required
        result['allow_dont_know'] = self.required
        if self.nodes:
            result['nodes'] = self.nodes
        return result