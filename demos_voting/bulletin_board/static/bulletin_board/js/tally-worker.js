var hmac = null;
var e = null;
var order = null;
var election = null;
var electionResult = null;
var csrfToken = null;

onmessage = function(event) {
    // Load the SJCL scripts.
    var sjclScriptUrls = event.data.sjclScriptUrls;
    for (var i = 0; i < sjclScriptUrls.length; i++) {
        importScripts(sjclScriptUrls[i]);
    }
    // CSRF token.
    csrfToken = event.data.csrfToken;
    // Fetch the election objects from the server.
    election = getHttpRequest(event.data.electionUrl + '?fields=ballots_url,coins,question_count,questions(option_count,blank_option_count)');
    // e is the challenger, which is the hash of all voter's coins.
    e = sjcl.bn.fromBits(sjcl.codec.base64.toBits(election.coins));
    // prime256v1 (a.k.a. secp256r1)
    order = sjcl.bn.fromBits(sjcl.codec.hex.toBits("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551"));
    // hmac is used as the PRF, key is the trustee's secret key.
    hmac = new sjcl.misc.hmac(sjcl.codec.base64.toBits(event.data.secretKey), sjcl.hash.sha256);
    // Prepare the election result.
    electionResult = {questions: []};
    for (var q = 0; q < election.questions.length; q++) {
        var optionCount = election.questions[q].option_count;
        var blankOptionCount = election.questions[q].blank_option_count;
        electionResult.questions.push({tally_decommitment: []});
    }
    // Iterate over the specified ballot range and do the processing.
    var offset = event.data.rangeStart;
    var limit = event.data.rangeStop - event.data.rangeStart;
    var ballotsUrl = election.ballots_url + '?fields=url,serial_number,parts(tag,is_cast,questions(index,options(index,is_voted)))&is_cast=true';
    while (true) {
        ballots = getHttpRequest(ballotsUrl + '&limit=' + limit + '&offset=' + offset)
        var ballotCount = ballots.results.length;
        for (var i = 0; i < ballotCount; i++) {
            ballot = ballots.results[i];
            processBallot(ballot);
            postMessage({type: 'progress', value: 1});
        }
        offset += ballotCount;
        limit -= ballotCount;
        if (limit == 0) {
            break;
        }
        ballotsUrl = ballots.next;
    }
    // Serialize the election result to base64 and send it to the main thread.
    for (var q = 0; q < election.questions.length; q++) {
        var optionCount = election.questions[q].option_count;
        var blankOptionCount = election.questions[q].blank_option_count;
        var tallyDecommitment = electionResult.questions[q].tally_decommitment;
        if (tallyDecommitment.length != 0) {
            for (var o = 0; o < optionCount - blankOptionCount; o++) {
                tallyDecommitment[o] = sjcl.codec.base64.fromBits(tallyDecommitment[o].toBits());
            }
        }
    }
    postMessage({type: 'result', value: electionResult});
    close();
}

function getHttpRequest(url) {
    var xhr  = new XMLHttpRequest()
    xhr.open('GET', url, false);  // synchronous request
    var data = null;
    xhr.onload = function () {
        if (xhr.status == 200) {
            data = JSON.parse(xhr.responseText);
        } else {
            throw new Error(xhr.responseText);
        }
    }
    xhr.send();
    return data;
}

function patchHttpRequest(url, data) {
    var xhr = new XMLHttpRequest();
    xhr.open('PATCH', url, false);  // synchronous request
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', csrfToken);
    xhr.onload = function () {
        if (xhr.status != 200) {
            throw new Error(xhr.responseText);
        }
    }
    xhr.send(JSON.stringify(data));
}

function processBallot(ballot) {
    var ballotResult = {parts: []};
    for (var p = 0; p < ballot.parts.length; p++) {
        var ballotPart = ballot.parts[p];
        var ballotPartResult = {questions: []};
        for (var q = 0; q < ballotPart.questions.length; q++) {
            var ballotQuestion = ballotPart.questions[q];
            var ballotQuestionResult = null;
            if (ballotPart.is_cast) {
                addToTallyDecommitment(ballot, ballotPart, ballotQuestion);
                ballotQuestionResult = generateZK2(ballot, ballotPart, ballotQuestion);
            } else {
                ballotQuestionResult = generateDecommitment(ballot, ballotPart, ballotQuestion);
            }
            ballotPartResult.questions.push(ballotQuestionResult);
        }
        ballotResult.parts.push(ballotPartResult);
    }
    patchHttpRequest(ballot.url, ballotResult);
}

function addToTallyDecommitment(ballot, ballotPart, ballotQuestion) {
    var optionCount = election.questions[ballotQuestion.index].option_count;
    var blankOptionCount = election.questions[ballotQuestion.index].blank_option_count;
    var tallyDecommitment = electionResult.questions[ballotQuestion.index].tally_decommitment;
    for (var i = 0; i < optionCount; i++) {
        var ballotOption = ballotQuestion.options[i];
        if (ballotOption.is_voted) {
            if (tallyDecommitment.length == 0) {
                for (var j = 0; j < optionCount - blankOptionCount; j++) {
                    tallyDecommitment.push(new sjcl.bn(0));
                }
            }
            for (var j = 0; j < optionCount - blankOptionCount; j++) {
                var m = [ballot.serial_number, ballotPart.tag, ballotQuestion.index, "rand", ballotOption.index, j].join(',');
                tallyDecommitment[j].addM(sjcl.bn.fromBits(hmac.encrypt(m)));
            }
        }
    }
}

function generateDecommitment(ballot, ballotPart, ballotQuestion) {
    var optionCount = election.questions[ballotQuestion.index].option_count;
    var blankOptionCount = election.questions[ballotQuestion.index].blank_option_count;
    var ballotQuestionResult = {options: []};
    for (var i = 0; i < optionCount; i++) {
        var ballotOption = ballotQuestion.options[i];
        var ballotOptionResult = {decommitment: []};
        ballotQuestionResult.options.push(ballotOptionResult);
        for (var j = 0; j < optionCount - blankOptionCount; j++) {
            var m = [ballot.serial_number, ballotPart.tag, ballotQuestion.index, "rand", ballotOption.index, j].join(',');
            ballotOptionResult.decommitment.push(sjcl.codec.base64.fromBits(hmac.encrypt(m)));
        }
    }
    return ballotQuestionResult;
}

function generateZK2(ballot, ballotPart, ballotQuestion) {
    var optionCount = election.questions[ballotQuestion.index].option_count;
    var blankOptionCount = election.questions[ballotQuestion.index].blank_option_count;
    var ballotQuestionResult = {options: [], zk2: []};
    for (var i = 0; i < optionCount; i++) {
        var ballotOption = ballotQuestion.options[i];
        var ballotOptionResult = {zk2: []};
        ballotQuestionResult.options.push(ballotOptionResult);
        for (var j = 0; j < optionCount - blankOptionCount; j++) {
            var delta = [];  // delta 1 - 6
            for (var l = 0; l < 6; l++) {
                var m = [ballot.serial_number, ballotPart.tag, ballotQuestion.index, "zk", ballotOption.index, j, l].join(',');
                delta.push(sjcl.bn.fromBits(hmac.encrypt(m)));
            }
            for (var a = 0; a < 3; a++) {
                var phi = delta[2 * a];
                phi.mulmod(e, order);
                phi.addM(delta[2 * a + 1]);
                ballotOptionResult.zk2.push(sjcl.codec.base64.fromBits(phi.toBits()));
            }
        }
        var delta_row = [];  // delta 7 - 12
        for (var l = 6; l < 12; l++) {
            var m = [ballot.serial_number, ballotPart.tag, ballotQuestion.index, "zk_row", ballotOption.index, l].join(',');
            delta_row.push(sjcl.bn.fromBits(hmac.encrypt(m)));
        }
        for(var a = 0; a < 3; a++) {
            var phi = delta_row[2 * a];
            phi.mulmod(e, order);
            phi.addM(delta_row[2 * a + 1]);
            ballotQuestionResult.zk2.push(sjcl.codec.base64.fromBits(phi.toBits()));
        }
    }
    for (var j = 0; j < optionCount - blankOptionCount; j++) {
        var delta_col = [];  // delta 13 - 14
        for (var l = 12; l < 14; l++) {
            var m = [ballot.serial_number, ballotPart.tag, ballotQuestion.index, "zk_col", j, l].join(',');
            delta_col.push(sjcl.bn.fromBits(hmac.encrypt(m)));
        }
        var phi = delta_col[0];
        phi.mulmod(e, order);
        phi.addM(delta_col[1]);
        ballotQuestionResult.zk2.push(sjcl.codec.base64.fromBits(phi.toBits()));
    }
    return ballotQuestionResult;
}
