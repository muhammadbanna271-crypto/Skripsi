const button=document.getElementById("showPassword");

const input=document.querySelector("input[type=password], input[type=text][name=password]");

button.addEventListener("click",()=>{

if(input.type==="password"){

input.type="text";

button.innerHTML='<i class="fa-solid fa-eye-slash"></i>';

}else{

input.type="password";

button.innerHTML='<i class="fa-solid fa-eye"></i>';

}

});