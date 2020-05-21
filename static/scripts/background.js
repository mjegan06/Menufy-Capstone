//Using the DOM, change the background. When it reaches the end, repeart the array.
function randombg() {
  let listOfPhotos = [
    "url('/static/images/bbq.jpg')",
    "url('/static/images/beans.jpg')",
    "url('/static/images/Beer_On_Bar_Counter.jpg')",
    "url('/static/images/beers.jpg')",
    "url('/static/images/cocktail.jpg')",
    "url('/static/images/cupcakes.jpg')",
    "url('/static/images/eat.jpg')",
    "url('/static/images/food.jpg')",
    "url('/static/images/hamburger.jpg')",
    "url('/static/images/italian-cuisine.jpg')",
    "url('/static/images/kitchen.jpg')",
    "url('/static/images/pizza.jpg')",
    "url('/static/images/platter.jpg')",
    "url('/static/images/seafood-platter.jpg')",
    "url('/static/images/sushi_1.jpg')",
    "url('/static/images/sushi_2.jpg')",
    "url('/static/images/sushi_3.jpg')",
    "url('/static/images/taco.jpg')"
  ];
  let counter = Math.floor(Math.random() * listOfPhotos.length) + 0;

  document.getElementById("randbg").style.backgroundImage = listOfPhotos[counter];
}