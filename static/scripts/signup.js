function checkPassword(theForm){
    if(theForm.password.value != theForm.password2.value){
        alert('The password conformation does not match');
        return false;
    } else {
        return true;
    }
}