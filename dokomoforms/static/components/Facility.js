var React = require('react');

var ResponseField = require('./baseComponents/ResponseField.js');
var ResponseFields = require('./baseComponents/ResponseFields.js');
var LittleButton = require('./baseComponents/LittleButton.js');

var FacilityRadios = require('./baseComponents/FacilityRadios.js');
var Select = require('./baseComponents/Select.js');

/*
 * Facilities question component
 *
 * props:
 *     @question: node object from survey
 *     @questionType: type constraint
 *     @language: current survey language
 *     @surveyID: current survey id
 *     @disabled: boolean for disabling all inputs
 *     @db: pouchdb database 
 *     @tree: Facility Tree object
 */
module.exports = React.createClass({
    getInitialState: function() {
        var self = this;
        var loc = JSON.parse(localStorage['location'] || '{}');
        var answer = this.getAnswer();
        var selectOff = answer && answer.metadata && answer.metadata.is_new;
        return { 
            loc: loc,
            selectFacility: !selectOff,
            facilities: self.getFacilities(loc),
            choices: [
                {'value': 'water', 'text': 'Water'}, 
                {'value': 'energy', 'text': 'Energy'}, 
                {'value': 'education', 'text': 'Education'}, 
                {'value': 'health', 'text': 'Health'}, 
            ],
        }
    },

    /*
     * Hack to force react to update child components
     * Gets called by parent element through 'refs' when state of something changed 
     * (usually localStorage)
     */
    update: function() {
        var survey = JSON.parse(localStorage[this.props.surveyID] || '{}');
        var answers = survey[this.props.question.id] || [];
        var length = answers.length === 0 ? 1 : answers.length;
        this.setState({
            questionCount: length,
        });
    },

    toggleAddFacility: function() {
        this.setState({
            selectFacility : this.state.selectFacility ? false : true
        })
    },

    selectFacility: function(option, data) {
        console.log("Selected facility");
        var survey = JSON.parse(localStorage[this.props.surveyID] || '{}');
        var answers = survey[this.props.question.id] || [];
        answers = [];

        this.state.facilities.forEach(function(facility) {
            if (facility.uuid === option) {
                answers = [{
                    'response': {
                        'facility_id': facility.uuid,
                        'facility_name': facility.name,
                        'facility_sector': facility.properties.sector,
                        'lat': facility.coordinates[1],
                        'lng': facility.coordinates[0],
                    }, 
                    'response_type': 'answer'
                }];
                return false;
            }
            return true;
        });

        survey[this.props.question.id] = answers;
        localStorage[this.props.surveyID] = JSON.stringify(survey);
        
    },

    getFacilities: function(loc) {
        if (!loc || !loc.lat || !loc.lng || !this.props.tree || !this.props.tree.root)
          return [];  

        console.log("Getting facilities ...");
        return this.props.tree.getNNearestFacilities(loc.lat, loc.lng, 1000, 10);
    },

    getAnswer: function() {
        var survey = JSON.parse(localStorage[this.props.surveyID] || '{}');
        var answers = survey[this.props.question.id] || [];
        console.log("Selected facility", answers[0]);
        if (answers[0]) 
            return answers[0]
    },

    /*
     * Generate objectID compatitable with Mongo for the Revisit API
     *
     * Returns an objectID string
     */
    createObjectID: function() {
       return 'xxxxxxxxxxxxxxxxxxxxxxxx'.replace(/[x]/g, function() {
           var r = Math.random()*16|0;
           return r.toString(16);
       });
    },

    onInput: function(type, value) {
        console.log("Dealing with input", value, type);
        var survey = JSON.parse(localStorage[this.props.surveyID] || '{}');
        var answers = survey[this.props.question.id] || [];
        var self = this;
        if (answers[0] && (!answers[0].metadata || !answers[0].metadata.is_new)) {
            answers = [];
        }

        // Load up previous response, update values
        var response = (answers[0] && answers[0].response) || {}; 
        var uuid = response.facility_id || this.createObjectID();
        response.facility_id = uuid;
        // XXX This kind of assumes that current lat/lng is correct at the time of last field update
        response.lat = this.state.loc.lat; 
        response.lng = this.state.loc.lng; 

        switch(type) {
            case 'text':
                response.facility_name = value;
                break;
            case 'select':
                var v = value[0]; // Only one ever
                console.log('Selected v', v);
                response.facility_sector = v;
                break;
            case 'other':
                console.log('Other v', value);
                response.facility_sector = value;
                break;
        }

        answers = [{
            'response': response,
            'response_type': 'answer',
            'metadata': {
                'is_new': true
            }
        }];

        console.log("Built response", answers);

        survey[this.props.question.id] = answers;
        localStorage[this.props.surveyID] = JSON.stringify(survey);
    },


    /*
     * Retrieve location and record into state on success.
     */
    onLocate: function() {
        var self = this;
        navigator.geolocation.getCurrentPosition(
            function success(position) {
                var loc = {
                    'lat': position.coords.latitude,
                    'lng': position.coords.longitude, 
                }

                // Record location for survey
                localStorage['location'] = JSON.stringify(loc);

                var facilities = self.getFacilities(loc);
                self.setState({
                    loc: loc,
                    facilities: facilities
                });
            }, 
            
            function error() {
                console.log("Location could not be grabbed");
            }, 
            
            {
                enableHighAccuracy: true,
                timeout: 20000,
                maximumAge: 0
            }
        );


    },
    render: function() {
        var answer = this.getAnswer();

        var hasLocation = this.state.loc && this.state.loc.lat && this.state.loc.lng;
        var isNew = answer && answer.metadata && answer.metadata.is_new;

        var choiceOptions = this.state.choices.map(function(choice) { return choice.value });
        console.log("Choice options", choiceOptions);
        var sector = answer && answer.response.facility_sector;
        var isOther = choiceOptions.indexOf(sector) === -1;
        console.log("isOther", sector, isOther);
        sector = isOther ? sector && 'other' : sector; 

        return (
                <span>
                {this.state.selectFacility ?
                    <span>
                    <LittleButton buttonFunction={this.onLocate}
                       icon={'icon-star'}
                       text={'find my location and show nearby facilities'} 
                    />
                    <FacilityRadios 
                        selectFunction={this.selectFacility} 
                        facilities={this.state.facilities}
                        initValue={answer && !isNew && answer.response.facility_id}
                    />

                    { hasLocation  ?
                        <LittleButton buttonFunction={this.toggleAddFacility}
                                text={'add new facility'} />
                        : null
                    }
                    </span>
                :
                    <span>
                    <ResponseField 
                        onInput={this.onInput.bind(null, 'text')}
                        initValue={isNew && answer.response.facility_name}
                        type={'text'}
                    />
                    <ResponseField 
                        initValue={JSON.stringify(this.state.loc)} 
                        type={'location'}
                        disabled={true}
                    />
                    <Select 
                        choices={this.state.choices} 
                        initValue={isNew && isOther ? answer.response.facility_sector : null}
                        initSelect={isNew && [sector]} 
                        withOther={true} 
                        multiSelect={false}
                        onInput={this.onInput.bind(null, 'other')}
                        onSelect={this.onInput.bind(null, 'select')}
                    />

                    <LittleButton 
                        buttonFunction={this.toggleAddFacility} 
                            text={'cancel'} 
                     />

                    </span>
                }
                </span>
               )
    }
});
