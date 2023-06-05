const FILE_DIR = "/static/ApiCodes/"
$(document).ready(function(){
    showResponse(0)
})
function copyApiKey() {
        const apiKeyField = document.getElementById('apiCode');
        const el = document.createElement('textarea');
        el.value = apiKeyField.value;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showSuccessMsg('Copied to clipboard!');
        return true;
    }

function copySourceCode(id) {
        const scode = document.getElementById(`${id}`).textContent;
        const el = document.createElement('textarea');
        el.value = scode;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showSuccessMsg('Copied to clipboard!');
        return true;
    }


function showSuccessMsg(message) {
        if (message) {
            var parentEle = document.getElementById('balance-main')
            if(!document.getElementById('errorField')){
            var msgDiv1 = document.createElement('div');
            msgDiv1.className = "alert-box-outer";
            msgDiv1.id = "errorField";
            }
            else{
                var msgDiv1 = document.getElementById('errorField');
            }
            if(!document.getElementById('errorField1')){
                var msgDiv2 = document.createElement('div');
                msgDiv2.className = "success-alert";
                msgDiv2.id = "errorField1";
                msgDiv2.style.display = 'block';
            }
            else{
                var msgDiv2 = document.getElementById('errorField1');
            }
            if(!document.getElementById('msgElem')){
                var msgElem = document.createElement('p');
                msgElem.setAttribute(
                    'style',
                    'text-align: center;',
                );
                msgElem.id = "msgElem";
            }
            else {
                var msgElem = document.getElementById('msgElem');
            }
            msgElem.innerText = message;
            msgDiv2.appendChild(msgElem)
            msgDiv1.appendChild(msgDiv2)
            parentEle.appendChild(msgDiv1);
            console.log("parentEle", parentEle)
            setTimeout(() => {
                document.getElementById('errorField').remove();
            }, 5000);
        }
    }



function showResponse(index) {
    const allLinks = document.getElementsByClassName("api-link");
    for (let i = 0; i < allLinks.length; i++) {
        allLinks[i].classList.remove("active");
    }
    const link = document.getElementById(`apiLink-${index}`);
    $(".api-title").html(link.textContent.trim())
    if (link) link.classList.add("active");
    $(".select-lang").attr("data-index",index)
    $(".select-lang").val("PHP");
    showCodeOfLang('PHP',index);
}

function copyApiKey() {
    const apiKeyField = document.getElementById('apiCode');
    const el = document.createElement('textarea');
    el.value = apiKeyField.value;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showSuccessMsg('Copied to clipboard!');
    return true;
}

function copySourceCode(id) {
    const scode = document.getElementById(`${id}`).textContent;
    const el = document.createElement('textarea');
    el.value = scode;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showSuccessMsg('Copied to clipboard!');
    return true;
}

function showCodeOfLang(value,index) {
    index = parseInt(index)
    switch (index) {
        case 0:
            displayLang(0, 'authentication', value);
            break;
        case 1:
            displayLang(1, 'get_accounts', value);
            break;
        case 2:
            displayLang(2, 'retrieve_single_account', value);
            break;
        case 3:
            displayLang(3, 'wire_transfer', value);
            break;
        case 4:
            displayLang(4, 'account_to_account', value);
            break;
        case 5:
            displayLang(5, 'currency_conversion', value);
            break;
        case 6:
            displayLang(6, 'userdetails', value);
            break;
        case 7:
            displayLang(7, 'transactions', value);
            break;
        case 8:
            displayLang(8, 'get_beneficiary', value);
            break;
        case 9:
            displayLang(9, 'create_beneficiary', value);
            break;
        case 10:
            displayLang(10, 'update_beneficiary', value);
            break;
        case 11:
            displayLang(11, 'delete_beneficiary', value);
            break;
        case 12:
            displayLang(12, 'checkout', value);
            break;
        
    }
}

function displayLang(cat, filename, lang) {
//    $(".api-title").html(filename) // update source code content title
   $.getJSON(FILE_DIR+filename+".json", function(data){ // read corresponding json file
        code_str = "";
        resp_str = "";
        parameter_content = ""
        console.log("data.endpoint",data.endpoint)
        $(".code-title-change").html(data.endpoint)
        for (language of data.languages){
            if (language.name == lang){
                code = language.code;
                for (code of language.code){
                    code_str = code_str.concat("\n"+code);
                }
                for (resp of language.Response){
                    resp_str = resp_str.concat("\n"+resp);
                }
                break;
            }
        }

        for (param of data.parameters){
            parameter_name = param.name
            required = param.required
            description = param.description
            choice=param.choices
            codes=param.country_codes
            showcode=param.contryid
            parameter_content = parameter_content.concat("<div> <h2 class='code-in-parameter'>"+parameter_name)
            if (required){
               parameter_content = parameter_content.concat(" <span style='color:#fa661d;font-size:12px'>Required</span></h2>")
            }
            if (choice){
            let choice_option = "";
            for (let i = 0; i < choice.length; i++) {
                choice_option += choice[i] + "<br>";
            }
                parameter_content = parameter_content.concat("<div style='background-color: #f5f5f5f5;padding:12px;padding-top: 15px;width:42%;height: 175px;border-radius: 4px;overflow-y: auto;'><span>"+choice_option+"</span></div>")
            }
            if (showcode){
            let codecountry = "";
            for (let i = 0; i < showcode.length; i++) {
                codecountry += showcode[i] + "<br>";
            }
                parameter_content = parameter_content.concat("<div style='margin-top: 7px;background-color: #f5f5f5f5;padding:12px;font-size:13px;padding-top: 15px;width:42%;height:175px;border-radius: 4px;overflow-y: auto;font-weight: 300;color: #4d4d4d;'><span>"+codecountry+"</span></div>")
            }
            if (codes){
            let country = "";
            for (let i = 0; i < codes.length; i++) {
                country += codes[i] + "<br>";
            }
                parameter_content = parameter_content.concat("<div style='background-color: #f5f5f5f5;padding:12px;padding-top: 15px;width:42%;height:175px;border-radius: 4px;overflow-y: auto;'><span>"+country+"</span></div>")
            }
            parameter_content = parameter_content.concat("<p style='font-size: 12px;margin-top: 7px;'>"+description+" </p> </div>")
        }
        const param_elem = document.getElementById(`code-for-parameter`);
        const code_elem = document.getElementById(`content-disp`);
        const resp_elem = document.getElementById(`response-disp`);
        param_elem.innerText = '';
        code_elem.innerText = '';
        resp_elem.innerText = '';
        if (parameter_content != ""){
            $("#parameter-content").show()
            $("#code-for-parameter").append(parameter_content);
        }else{
            $("#parameter-content").hide()
        }
        code_elem.innerText = code_str;
        resp_elem.innerText = resp_str;
    }).fail(function(){
        console.log("An error has occurred.");
    });
}

