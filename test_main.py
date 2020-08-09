from main import *
import pytest

# Tests are parametrised using parameters in the JSON files stored in 'examples/'
# You can add, delete, edit JSON files in the folder by following the FIRE data format.
# JSON files tested will need to containt at least parameters in the examples given
# otherwise tests will return an error.


@pytest.fixture(params=['data', 'data1', 'data2'])
def testCase(request):
    with open("examples/{}.json".format(request.param), 'r') as f:
        data = json.load(f)
    instruments = [Instrument(item) for item in data['data']]
    process = SA_CCR(instruments)
    return {
        "data": data,
        "instruments": instruments,
        "process": process
    }


def testJson(testCase):
    assert testCase['data']['name'] == 'Derivatives Data'
    assert testCase['data']['data'] != None
    assert len([x for x in testCase['data']['data']]) > 1


def testTypes(testCase):

    for instrument in testCase['instruments']:
        assert type(instrument) == Instrument
        assert type(instrument.getAdjustedNotional()) == np.float64
        assert type(instrument.getDelta()) == float
        assert type(instrument.getBucketSet()) == int
        assert type(instrument.getEffectiveNotional()) == np.float64

    testCase['process'].initialize()
    testCase['process'].getEffectiveNotionalAmount()

    assert type(testCase['process']) == SA_CCR
    assert type(testCase['process'].getReplacementCost()) == float
    assert type(testCase['process'].getAddOn()) == np.float64
    assert type(testCase['process'].getEAD()) == np.float64


def test_calcNotionalAmount(testCase):
    a, b, c = np.random.random_sample((3,))
    assert type(testCase['process'].calcNotionalAmount([a, b, c])) == np.float64
    result = (a**2 + b**2 + c**2 + 1.4*a*b + 1.4*a*c + 0.6*b*c)**0.5
    assert testCase['process'].calcNotionalAmount([a, b, c]) == result

    a, b = np.random.random_sample((2,))
    c = 0.0
    assert type(testCase['process'].calcNotionalAmount([a, b])) == np.float64
    result = (a**2 + b**2 + c**2 + 1.4*a*b + 1.4*a*c + 0.6*b*c)**0.5
    assert testCase['process'].calcNotionalAmount([a, b, c]) == result

    a = np.random.random_sample()
    b = c = 0.0
    assert type(testCase['process'].calcNotionalAmount([a, b])) == float
    result = (a**2 + b**2 + c**2 + 1.4*a*b + 1.4*a*c + 0.6*b*c)**0.5
    assert testCase['process'].calcNotionalAmount([a, b, c]) == result


def test_getReplacementCost(testCase):
    for item in testCase['instruments']:
        item.mtm_dirty = -100
    assert testCase['process'].getReplacementCost() == 0

    for item in testCase['instruments']:
        item.mtm_dirty = 200
    assert testCase['process'].getReplacementCost() >= 200
