import * from 'some/file/path'
import Import from 'some/file/path.js'
import { import, test, } from '/some/file/path.js'
import { import as test } from 'test'

export default { reexport } from 'file.mjs'
export Claass
export { var1, var2 }

function (param) {
	({ overwrite: param } = by.destructuring())
}

async function (param) {
	({ overwrite: param } = await by.destructuring())
}

function withFunctionAsParamDefault(          param1, param2 =       function () {}) { /**/ }
function withAsyncFunctionAsParamDefault(     param1, param2 = async function () {}) { /**/ }
function withArrowFunctionAsParamDefault(     param1, param2 =       () => {}) { /**/ }
function withAsyncArrowFunctionAsParamDefault(param1, param2 = async () => {}) { /**/ }

callWArrowFunction(                                 'argument',       () => { /**/ })
callWAsyncArrowFunction(                            'argument', async () => { /**/ })
callWArrowFunctionWFunctionAsParamDefault(          'argument',       (arrowParam = function () {}) => { /**/ })
callWAsyncArrowFunctionWFunctionAsParamDefault(     'argument', async (arrowParam = function () {}) => { /**/ })
callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = () => {}) => { /**/ })
callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = () => {}) => { /**/ })

method.callWArrowFunction(                                 'argument',       () => { /**/ })
method.callWAsyncArrowFunction(                            'argument', async () => { /**/ })
method.callWArrowFunctionWFunctionAsParamDefault(          'argument',       (arrowParam = function () {}) => { /**/ })
method.callWAsyncArrowFunctionWFunctionAsParamDefault(     'argument', async (arrowParam = function () {}) => { /**/ })
method.callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = () => {}) => { /**/ })
method.callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = () => {}) => { /**/ })


function withFunctionAsParamDefault(          param1, param2 =       function (functionParam = () => {}) {}) { /**/ }
function withAsyncFunctionAsParamDefault(     param1, param2 = async function (functionParam = () => {}) {}) { /**/ }
function withFunctionAsParamDefault(          param1, param2 =       function (functionParam = arrowParamInner => {}) {}) { /**/ }
function withAsyncFunctionAsParamDefault(     param1, param2 = async function (functionParam = arrowParamInner => {}) {}) { /**/ }
function withArrowFunctionAsParamDefault(     param1, param2 =       (arrowParam = () => {}) => {}) { /**/ }
function withAsyncArrowFunctionAsParamDefault(param1, param2 = async (arrowParam = () => {}) => {}) { /**/ }
function withArrowFunctionAsParamDefault(     param1, param2 =       (arrowParam = arrowParamInner => {}) => {}) { /**/ }
function withAsyncArrowFunctionAsParamDefault(param1, param2 = async (arrowParam = arrowParamInner => {}) => {}) { /**/ }

callWArrowFunction(                                 'argument',       arrowParam => { /**/ })
callWAsyncArrowFunction(                            'argument', async arrowParam => { /**/ })
callWArrowFunctionWFunctionAsParamDefault(          'argument',       (arrowParam = function () {}) => { /**/ })
callWAsyncArrowFunctionWFunctionAsParamDefault(     'argument', async (arrowParam = function () {}) => { /**/ })
callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = () => {}) => { /**/ })
callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = () => {}) => { /**/ })
callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = arrowParamInner => {}) => { /**/ })
callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = arrowParamInner => {}) => { /**/ })

method.callWArrowFunction(                                 'argument',       arrowParam => { /**/ })
method.callWAsyncArrowFunction(                            'argument', async arrowParam => { /**/ })
method.callWArrowFunctionWFunctionAsParamDefault(          'argument',       (arrowParam = function () {}) => { /**/ })
method.callWAsyncArrowFunctionWFunctionAsParamDefault(     'argument', async (arrowParam = function () {}) => { /**/ })
method.callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = () => {}) => { /**/ })
method.callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = () => {}) => { /**/ })
method.callWArrowFunctionWArrowFunctionAsParamDefault(     'argument',       (arrowParam = arrowParamInner => {}) => { /**/ })
method.callWAsyncArrowFunctionWArrowFunctionAsParamDefault('argument', async (arrowParam = arrowParamInner => {}) => { /**/ })

//
// ------------------------------------------------------------------------------------------------
//


const SOURCE_DIR = './test-source/'

async function main([targetVersion]) {
	try {
		({ name: targetVersion } = await fetchRepoTagData(targetVersion))
	} catch (err) {
		oops(err, { exit: false })

		return oops('✘ TESTS FAILED')
	}

	let stdout = ''
	let stderr = ''

	;({ stdout, stderr } = spawnSync('node', `test/scripts/foo.js ${targetVersion}`.split(' '), { encoding: 'utf8' }))

	console.log(stdout)

	console.log('All good.', color.green('\n\n✔ TESTS PASSED'))
	process.exit(0)
}

main(process.argv.slice(2))
